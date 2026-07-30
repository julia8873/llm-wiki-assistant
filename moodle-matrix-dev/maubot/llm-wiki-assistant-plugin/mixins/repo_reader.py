import os
import asyncio
import logging
import urllib.parse
from typing import Dict, Any, List
from .vector_store import VectorStore
from .llm_clients import LLMClient

logger = logging.getLogger("llm_wiki.repo_reader")

class RepoReaderError(Exception):
    pass

class RepoReader:
    def __init__(self, config: Dict[str, Any], vector_store: VectorStore, llm_client: LLMClient):
        self.config = config
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.repos_dir = "/tmp/llm_wiki_repos"
        os.makedirs(self.repos_dir, exist_ok=True)
        
        self.git_config = self.config.get("git", {})
        
    def _get_token_for_provider(self, git_provider: str) -> str:
        provider_config = self.git_config.get(git_provider, {})
        env_var = provider_config.get("token_env_var", "")
        if not env_var and git_provider == "github":
            env_var = provider_config.get("pat_env_var", "GITHUB_PAT")
            
        token = os.environ.get(env_var)
        if not token:
            logger.warning(f"No token found for provider {git_provider} in env var {env_var}")
            return ""
        return token

    def _inject_token(self, url: str, git_provider: str) -> str:
        token = self._get_token_for_provider(git_provider)
        if not token:
            return url
            
        parsed = urllib.parse.urlparse(url)
        # Para GitHub, el auth suele ser token@... o x-access-token:token@...
        # Para GitLab suele ser oauth2:token@... o simplemente un nombre:token
        # Para simplificar y hacerlo agnóstico en HTTPS git moderno, suele valer username:token o solo token
        if git_provider == "github":
            auth = f"{token}@"
        elif git_provider == "gitlab":
            auth = f"oauth2:{token}@"
        else:
            auth = f"llm_bot:{token}@"
            
        netloc = auth + parsed.netloc
        return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    async def clone_or_update(self, repo_url: str, git_provider: str) -> str:
        """Clona o actualiza el repositorio y devuelve la ruta local."""
        # Sanitizar nombre de carpeta
        safe_name = urllib.parse.quote_plus(repo_url)
        local_path = os.path.join(self.repos_dir, safe_name)
        
        auth_url = self._inject_token(repo_url, git_provider)
        
        if os.path.exists(os.path.join(local_path, ".git")):
            # Update
            logger.debug(f"Actualizando repositorio en {local_path}")
            proc = await asyncio.create_subprocess_shell(
                "git pull",
                cwd=local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            # Clone
            logger.debug(f"Clonando repositorio en {local_path}")
            proc = await asyncio.create_subprocess_shell(
                f"GIT_TERMINAL_PROMPT=0 git clone {auth_url} {local_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error_msg = stderr.decode()
            # Ocultar token en los logs
            token = self._get_token_for_provider(git_provider)
            if token:
                error_msg = error_msg.replace(token, "***")
            raise RepoReaderError(f"Error en Git: {error_msg}")
            
        return local_path

    def _chunk_text(self, text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            chunks.append(text[start:end])
            start += (max_chars - overlap)
        return chunks

    async def index_repository(self, repo_url: str, local_path: str):
        """Lee los ficheros OKF (.md, .txt) y los guarda en pgvector."""
        logger.info(f"Indexando repositorio: {repo_url}")
        
        okf_config = self.config.get("okf", {})
        allowed_exts = okf_config.get("extensiones_permitidas", [".md", ".txt"])
        
        # Eliminar chunks antiguos
        await self.vector_store.clear_repo(repo_url)
        
        chunks_to_insert = []
        
        for root, _, files in os.walk(local_path):
            if ".git" in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, local_path)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        continue
                        
                    text_chunks = self._chunk_text(content)
                    
                    for text_chunk in text_chunks:
                        if not text_chunk.strip():
                            continue
                        
                        try:
                            # Conseguir embedding usando el cliente LLM
                            embedding = await self.llm_client.get_embedding(text_chunk)
                            chunks_to_insert.append({
                                "file_path": rel_path,
                                "content": text_chunk,
                                "embedding": embedding
                            })
                        except Exception as e:
                            logger.error(f"Error generando embedding para {rel_path}: {e}")
                            
        # Guardar en postgres
        if chunks_to_insert:
            await self.vector_store.add_chunks(repo_url, chunks_to_insert)
            logger.info(f"Indexados {len(chunks_to_insert)} chunks para {repo_url}")

    async def process_repository(self, repo_url: str, git_provider: str):
        """Flujo completo: clona/actualiza e indexa."""
        local_path = await self.clone_or_update(repo_url, git_provider)
        await self.index_repository(repo_url, local_path)

    async def search(self, repo_url: str, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Busca en el repositorio usando RAG."""
        query_embedding = await self.llm_client.get_embedding(query)
        results = await self.vector_store.search(repo_url, query_embedding, limit)
        return results
