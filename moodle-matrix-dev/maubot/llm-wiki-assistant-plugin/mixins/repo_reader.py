import os
import asyncio
import logging
import urllib.parse
import json
from datetime import datetime
from typing import Dict, Any, List
import pypdf
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

    async def process_repository(self, mapeo_data: Dict[str, Any]):
        """Flujo completo: clona/actualiza e indexa."""
        repo_url = mapeo_data.get('repo_url')
        official_repo_url = mapeo_data.get('official_repo_url')
        from git_utils import asegurar_repo_local
        safe_name = urllib.parse.quote_plus(repo_url)
        local_path = os.path.join(self.repos_dir, safe_name)
        await asegurar_repo_local(repo_url, official_repo_url, local_path)
        await self.index_repository(repo_url, local_path)

    async def search(self, mapeo_data: Dict[str, Any], query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Busca en el repositorio usando RAG."""
        repo_url = mapeo_data.get('repo_url')
        query_embedding = await self.llm_client.get_embedding(query)
        results = await self.vector_store.search(repo_url, query_embedding, limit)
        
        # Filtrar si el profesor está en modo carpeta
        is_teacher = mapeo_data.get("is_teacher", False)
        teacher_mode = mapeo_data.get("teacher_mode", "oficial")
        moodle_username = mapeo_data.get("moodle_username", "unknown")
        
        if is_teacher and teacher_mode == "carpeta":
            prefix = f"profesores/{moodle_username}/"
            results = [r for r in results if r["file_path"].startswith(prefix)]
            
        return results

    async def ingest_file_okf(self, file_bytes: bytes, filename: str, mapeo_data: Dict[str, Any], with_ocr: bool = False) -> None:
        """! 
        @brief Ingesta un archivo al repositorio siguiendo el formato OKF v0.1.
        """
        repo_url = mapeo_data.get('repo_url')
        official_repo_url = mapeo_data.get('official_repo_url')
        git_provider = mapeo_data.get('git_provider')
        is_teacher = mapeo_data.get("is_teacher", False)
        moodle_username = mapeo_data.get("moodle_username", "unknown")
        
        base_dir = f"profesores/{moodle_username}" if is_teacher else "."
        
        from git_utils import asegurar_repo_local
        safe_name = urllib.parse.quote_plus(repo_url)
        local_path = os.path.join(self.repos_dir, safe_name)
        await asegurar_repo_local(repo_url, official_repo_url, local_path)
        
        # 1. Guardar el original en raw/
        raw_dir = os.path.join(local_path, base_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        file_path = os.path.join(raw_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        # 2. Extraer texto (Normal o OCR)
        extracted_text = ""
        ext = os.path.splitext(filename)[1].lower()
        if with_ocr and hasattr(self.llm_client, "get_response_with_file"):
            system_prompt = "Eres un sistema OCR. Extrae todo el texto legible de este documento/imagen de la forma mas fiel posible. Ignora ruido de fondo."
            extracted_text = await self.llm_client.get_response_with_file(system_prompt, "Por favor, extrae el texto de este documento.", file_bytes, "application/pdf" if ext == ".pdf" else "image/jpeg")
        else:
            if ext == ".pdf":
                import io
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                except Exception as e:
                    logger.error(f"Error extrayendo texto del PDF localmente: {e}")
                    raise RepoReaderError(f"No se pudo extraer texto del PDF: {e}")
            else:
                extracted_text = file_bytes.decode('utf-8', errors='ignore')
                
        # 3. Leer AGENTS.md para inyectarlo como contexto (si existe)
        agents_md_path = os.path.join(local_path, base_dir, "AGENTS.md")
        if not os.path.exists(agents_md_path):
            if is_teacher:
                agents_md_path = os.path.join(local_path, "AGENTS.md") # Repositorio oficial
            else:
                agents_md_path = os.path.join(local_path, "material-oficial", "AGENTS.md")
        
        agents_content = ""
        if os.path.exists(agents_md_path):
            with open(agents_md_path, "r", encoding="utf-8") as f:
                agents_content = f.read()
                
        # 4. Extraer conceptos usando el LLM y evaluar la calidad de la extracción
        prompt_conceptos = (
            "Analiza el siguiente texto extraído de un documento. Si notas que el texto es ilegible, es ruido, tiene muchísimos caracteres extraños o no tiene sentido (indicando una mala extracción), "
            "DEBES rechazarlo devolviendo EXCLUSIVAMENTE este JSON: {\"error\": \"mala_extraccion\"}.\n\n"
            "Si el texto es legible, debes ejecutar la operación 'INGEST' sobre él, basándote en la documentación de AGENTS.md proporcionada.\n"
            "IMPORTANTE: Las rutas de destino en este repositorio son diferentes a las de AGENTS.md. Debes usar estas equivalencias:\n"
            "- 'okf/concepts/' -> 'conceptos/'\n"
            "- 'okf/entities/' -> 'entidades/'\n"
            "- 'okf/sources/' -> 'recursos/'\n\n"
            "NO DEVUELVAS JSON. Devuelve tu respuesta EXCLUSIVAMENTE utilizando estas etiquetas XML para estructurar los ficheros que vas a crear:\n\n"
            "<file path=\"recursos/nombre_fuente.md\">\n"
            "---\n"
            "type: Source\n"
            "title: ...\n"
            "...\n"
            "---\n"
            "\n"
            "Resumen del documento...\n"
            "</file>\n\n"
            "<file path=\"conceptos/concepto_extraido.md\">\n"
            "---\n"
            "type: Concept\n"
            "...\n"
            "---\n"
            "\n"
            "Contenido del concepto...\n"
            "</file>\n\n"
            "Si el texto es basura (ruido/mala extracción), simplemente devuelve <error>mala_extraccion</error>.\n\n"
            f"--- TEXTO EXTRAIDO DEL DOCUMENTO ---\n{extracted_text}"
        )
        
        system_prompt = "Eres un asistente de organización OKF. Debes asegurar la calidad del texto y estructurar conocimiento usando estrictamente las etiquetas <file> indicadas.\n\n"
        if agents_content:
            system_prompt += f"--- REGLAS OKF (AGENTS.md) ---\n{agents_content}\n"
            
        respuesta_llm = await self.llm_client.get_response(system_prompt, prompt_conceptos, max_tokens_override=8192)
        
        # Comprobar si la IA determinó que la extracción era mala
        if "<error>mala_extraccion</error>" in respuesta_llm:
            raise RepoReaderError(
                "La extracción de texto ha fallado o el contenido es ilegible. "
                "No se subirá nada al repositorio para evitar ensuciarlo con datos erróneos. "
                "Te recomiendo que lo intentes de nuevo utilizando la opción 'ocr'."
            )
            
        # Parsear las etiquetas XML <file path="...">...</file>
        import re
        file_matches = re.findall(r'<file\s+path=["\']([^"\']+)["\']>\s*(.*?)\s*</file>', respuesta_llm, flags=re.DOTALL | re.IGNORECASE)
        
        if not file_matches:
            logger.error(f"El LLM no devolvió ninguna etiqueta <file>: {respuesta_llm}")
            raise RepoReaderError("El LLM no devolvió ningún archivo formateado correctamente en etiquetas XML.")
            
        # 5. Crear los ficheros Markdown en sus respectivas carpetas
        archivos_creados = []
        
        for path_rel, content in file_matches:
            file_path_rel = os.path.join(base_dir, path_rel.strip())
            file_content = content.strip() + "\n"
                
            if not file_path_rel or not file_content:
                continue
                
            # Asegurar que el directorio existe
            full_path = os.path.join(local_path, file_path_rel)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as out_f:
                out_f.write(file_content)
            archivos_creados.append(file_path_rel)
            
        # 6. Escribir en bitacora/log.md
        bitacora_dir = os.path.join(local_path, base_dir, "bitacora")
        os.makedirs(bitacora_dir, exist_ok=True)
        log_path = os.path.join(bitacora_dir, "log.md")
        
        fecha = datetime.now().strftime("%Y-%m-%d")
        modo_extraccion = "OCR Multimodal (Gemini)" if with_ocr else "Extracción de texto normal (PyPDF)"
        log_entry = f"\n\n## [{fecha}] ingest | {filename}\n"
        log_entry += f"- **Archivo origen**: `raw/{filename}`\n"
        log_entry += f"- **Método de extracción**: {modo_extraccion}\n"
        log_entry += f"- **Archivos OKF creados/modificados**:\n"
        for a in archivos_creados:
            log_entry += f"  - `{a}`\n"
            
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        # 7. Comitear a Github
        await self._run_git_command("git add .", local_path)
        await self._run_git_command('git config user.email "bot@llm-wiki.com"', local_path)
        await self._run_git_command('git config user.name "LLM Wiki Bot"', local_path)
        try:
            await self._run_git_command(f'git commit -m "Ingesta automatica de conceptos desde {filename}"', local_path)
            await self._run_git_command("git push", local_path)
        except Exception as e:
            if "nothing to commit" not in str(e).lower():
                raise

    async def revert_last_ingest(self, mapeo_data: Dict[str, Any]) -> bool:
        """! 
        @brief Revierte la ultima operacion de ingesta OKF en el repositorio.
        
        Comprueba si el ultimo commit corresponde a una ingesta automatica. De ser asi,
        ejecuta un `git revert`, documenta los archivos borrados en la bitacora y hace push.
        
        @param mapeo_data Diccionario de datos del mapeo (repo, provieder, roles, etc).
        @return True si se pudo revertir exitosamente, False si la ultima accion no era una ingesta.
        @throws RepoReaderError si falla la operacion de git o hay conflictos.
        """
        repo_url = mapeo_data.get('repo_url')
        official_repo_url = mapeo_data.get('official_repo_url')
        git_provider = mapeo_data.get('git_provider')
        is_teacher = mapeo_data.get("is_teacher", False)
        moodle_username = mapeo_data.get("moodle_username", "unknown")
        
        base_dir = f"profesores/{moodle_username}" if is_teacher else "."
        from git_utils import asegurar_repo_local
        safe_name = urllib.parse.quote_plus(repo_url)
        local_path = os.path.join(self.repos_dir, safe_name)
        await asegurar_repo_local(repo_url, official_repo_url, local_path)
        
        # Comprobar el ultimo commit
        try:
            last_commit_msg = await self._run_git_command("git log -1 --pretty=%B", local_path)
        except Exception as e:
            logger.error(f"Error comprobando ultimo commit: {e}")
            raise RepoReaderError("No se pudo leer el historial del repositorio.")
            
        if "Ingesta automatica de conceptos" not in last_commit_msg:
            return False # No era una ingesta automatica
            
        # Extraer que ficheros se van a borrar
        try:
            files_to_revert = await self._run_git_command('git show -1 --name-only --format=""', local_path)
            files_list = [f.strip() for f in files_to_revert.split('\n') if f.strip() and "bitacora" not in f.lower()]
        except Exception as e:
            logger.error(f"Error sacando lista de ficheros a revertir: {e}")
            files_list = []
            
        # Revertir sin comitear aun
        try:
            await self._run_git_command("git revert HEAD --no-commit", local_path)
        except Exception as e:
            # Si hay conflictos (ej. alguien mas hizo commit), abortar reversion
            await self._run_git_command("git revert --abort", local_path)
            raise RepoReaderError(f"No se pudo revertir la ultima ingesta debido a conflictos de Git: {e}")
            
        # Anadir a la bitacora
        bitacora_dir = os.path.join(local_path, base_dir, "bitacora")
        os.makedirs(bitacora_dir, exist_ok=True)
        log_path = os.path.join(bitacora_dir, "log.md")
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n\n## [{fecha}] revert | Reversion de ultima ingesta\n"
        log_entry += "- **Archivos OKF eliminados permanentemente**:\n"
        if files_list:
            for f in files_list:
                log_entry += f"  - `{f}`\n"
        else:
            log_entry += "  - (Archivos del último commit)\n"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        # Comitear la reversion
        log_repo_path = os.path.join(base_dir, "bitacora", "log.md").replace("\\", "/")
        await self._run_git_command(f"git add {log_repo_path}", local_path)
        await self._run_git_command('git config user.email "bot@llm-wiki.com"', local_path)
        await self._run_git_command('git config user.name "LLM Wiki Bot"', local_path)
        await self._run_git_command('git commit -m "Reversion automatica de la ultima ingesta"', local_path)
        await self._run_git_command("git push", local_path)
        
        return True
                
    async def _run_git_command(self, cmd: str, cwd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"Git command failed: {stderr.decode('utf-8', errors='ignore')}")
        return stdout.decode('utf-8', errors='ignore')
