import os
import httpx
import logging
from .base import GitProviderClient, GitLabRateLimitError
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitLabProvisionError(Exception):
    pass

class GitLabProvider(GitProviderClient):
    def __init__(self, config: dict):
        self.config = config
        self.org = config['git']['gitlab']['grupo_destino']
        self.api_base = config['git']['gitlab']['api_base_url']
        
        env_var = config['git']['gitlab'].get('token_env_var', 'GITLAB_TOKEN')
        # Buscamos en env_var directamente, o en settings, o si el propio env_var parece un token
        self.token = getattr(settings, env_var, None) or os.getenv(env_var) or config['git']['gitlab'].get('pat')
        if not self.token and env_var.startswith("glpat-"):
            self.token = env_var
        
        if not self.token:
            raise GitLabProvisionError(f"{env_var} no está configurado")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.api_base, headers=self.headers)

    def _check_response(self, res: httpx.Response):
        if res.status_code == 429:
            retry_after = res.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                raise GitLabRateLimitError("GitLab rate limit exceeded", int(retry_after))
            
            reset_time = res.headers.get("RateLimit-Reset")
            if reset_time and reset_time.isdigit():
                import time
                wait_seconds = max(int(reset_time) - int(time.time()), 0)
                raise GitLabRateLimitError("GitLab rate limit exceeded", wait_seconds)

    async def existe_repo(self, repo_url_or_name: str) -> bool:
        repo_name = repo_url_or_name.split('/')[-1].replace('.git', '')
        project_path = f"{self.org}/{repo_name}".replace("/", "%2F")
        async with await self._get_client() as client:
            res = await client.get(f"/projects/{project_path}")
            self._check_response(res)
            return res.status_code == 200

    async def crear_repo_oficial(self, nombre_asignatura: str, template_id: str = None) -> str:
        # En GitLab, primero hacemos fork y luego eliminamos la relación.
        repo_oficial = f"{nombre_asignatura}-Oficial"
        template = template_id or self.config['git']['repo_plantilla']
        template_path = f"{self.org}/{template}".replace("/", "%2F")
        
        if await self.existe_repo(repo_oficial):
            logger.info(f"El repositorio oficial GitLab {self.org}/{repo_oficial} ya existe.")
            return f"{self.api_base.split('/api')[0]}/{self.org}/{repo_oficial}.git"

        async with await self._get_client() as client:
            logger.info(f"Haciendo fork de {template_path} a {repo_oficial}...")
            # En GitLab necesitamos el ID del namespace destino para hacer fork, o pasarlo en los params
            # Para simplificar, pasaremos el namespace_path
            res = await client.post(
                f"/projects/{template_path}/fork",
                json={
                    "name": repo_oficial,
                    "path": repo_oficial,
                    "namespace_path": self.org,
                    "visibility": "private"
                }
            )
            self._check_response(res)
            
            if res.status_code in (201, 200):
                repo_data = res.json()
                project_id = repo_data['id']
                
                # Eliminar relación de fork
                logger.info(f"Eliminando relación de fork para {repo_oficial}...")
                del_res = await client.delete(f"/projects/{project_id}/fork")
                self._check_response(del_res)
                if del_res.status_code != 204:
                    logger.warning(f"No se pudo eliminar el fork link de {repo_oficial}")
                    
                return repo_data.get("http_url_to_repo")
            else:
                raise GitLabProvisionError(f"Error al hacer fork (GitLab): {res.status_code} {res.text}")

    async def marcar_como_template(self, repo_url: str) -> None:
        # GitLab CE/EE gestiona los templates a nivel de instancia o de grupo.
        # En la API normal no hay un "is_template" bool al estilo GitHub.
        pass

    async def generar_repo_alumno(self, nombre_repo: str, repo_oficial_url: str) -> str:
        if await self.existe_repo(nombre_repo):
            logger.info(f"El repositorio {self.org}/{nombre_repo} ya existe.")
            return f"{self.api_base.split('/api')[0]}/{self.org}/{nombre_repo}.git"
            
        # Generar a partir del template original en lugar del repo_oficial
        # para evitar copiar carpetas de otros profesores.
        template = self.config['git']['repo_plantilla']
        template_path = f"{self.org}/{template}".replace("/", "%2F")

        async with await self._get_client() as client:
            logger.info(f"Haciendo fork alumno de {template_path} a {nombre_repo}...")
            res = await client.post(
                f"/projects/{template_path}/fork",
                json={
                    "name": nombre_repo,
                    "path": nombre_repo,
                    "namespace_path": self.org,
                    "visibility": "private"
                }
            )
            self._check_response(res)
            
            if res.status_code in (201, 200):
                repo_data = res.json()
                project_id = repo_data['id']
                
                logger.info(f"Eliminando relación de fork para {nombre_repo}...")
                del_res = await client.delete(f"/projects/{project_id}/fork")
                self._check_response(del_res)
                if del_res.status_code != 204:
                    logger.warning(f"No se pudo eliminar el fork link de {nombre_repo}")
                    
                return repo_data.get("http_url_to_repo")
            else:
                raise GitLabProvisionError(f"Error al aprovisionar {self.org}/{nombre_repo}: HTTP {res.status_code} {res.text}")
