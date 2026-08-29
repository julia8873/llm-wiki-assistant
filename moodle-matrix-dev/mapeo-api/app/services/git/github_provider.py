import os
import httpx
import logging
from .base import GitProviderClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubProvisionError(Exception):
    pass

class GitHubProvider(GitProviderClient):
    def __init__(self, config: dict):
        self.config = config
        self.org = config['git']['organizacion']
        self.api_base = config['git']['github']['api_base_url']
        self.template_repo = config['git']['repo_plantilla']
        
        # Leemos el PAT del entorno o configuración
        env_var = config['git']['github'].get('pat_env_var', 'GITHUB_PAT')
        self.pat = (getattr(settings, env_var, None) or os.getenv(env_var) or config['git']['github'].get('pat'))
        
        if not self.pat:
            raise GitHubProvisionError(f"{env_var} no está configurado")

        self.headers = {
            "Authorization": f"token {self.pat}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.api_base, headers=self.headers)

    async def existe_repo(self, repo_url_or_name: str) -> bool:
        repo_name = repo_url_or_name.split('/')[-1].replace('.git', '')
        async with await self._get_client() as client:
            res = await client.get(f"/repos/{self.org}/{repo_name}")
            return res.status_code == 200

    async def crear_repo_oficial(self, nombre_asignatura: str, template_id: str = None) -> str:
        repo_oficial = f"{nombre_asignatura}-Oficial"
        template = template_id or self.template_repo

        async with await self._get_client() as client:
            check_res = await client.get(f"/repos/{self.org}/{repo_oficial}")
            if check_res.status_code == 200:
                logger.info(f"El repositorio oficial {self.org}/{repo_oficial} ya existe.")
                return check_res.json().get("clone_url", f"https://github.com/{self.org}/{repo_oficial}.git")
            elif check_res.status_code != 404:
                raise GitHubProvisionError(f"Error comprobando {self.org}/{repo_oficial}: HTTP {check_res.status_code}")

            logger.info(f"Generando {self.org}/{repo_oficial} a partir de {template}...")
            gen_res = await client.post(
                f"/repos/{self.org}/{template}/generate",
                json={
                    "owner": self.org,
                    "name": repo_oficial,
                    "private": True,
                    "include_all_branches": False
                }
            )
            
            if gen_res.status_code in (201, 200, 422):
                repo_data = gen_res.json()
                if gen_res.status_code == 422:
                    repo_url = f"https://github.com/{self.org}/{repo_oficial}.git"
                else:
                    repo_url = repo_data.get("clone_url", f"https://github.com/{self.org}/{repo_oficial}.git")
                
                await self.marcar_como_template(repo_url)
                await self.registrar_webhook(repo_url)
                return repo_url
            else:
                raise GitHubProvisionError(f"Error al generar {self.org}/{repo_oficial}: HTTP {gen_res.status_code}")

    async def registrar_webhook(self, repo_url: str) -> None:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        target_url = getattr(settings, 'PUBLIC_API_URL', os.getenv('PUBLIC_API_URL'))
        if not target_url:
            logger.warning(f"No PUBLIC_API_URL set, skipping webhook registration for {repo_name}")
            return
            
        webhook_url = f"{target_url.rstrip('/')}/sync/oficial-updated"
        secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', os.getenv('GITHUB_WEBHOOK_SECRET'))
        if not secret:
            logger.warning(f"No GITHUB_WEBHOOK_SECRET set, skipping webhook registration for {repo_name}")
            return

        async with await self._get_client() as client:
            res = await client.post(
                f"/repos/{self.org}/{repo_name}/hooks",
                json={
                    "name": "web",
                    "active": True,
                    "events": ["push"],
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": secret
                    }
                }
            )
            if res.status_code not in (200, 201):
                logger.warning(f"Failed to register webhook for {repo_name}: HTTP {res.status_code} {res.text}")
            else:
                logger.info(f"Successfully registered webhook for {repo_name} pointing to {webhook_url}")

    async def marcar_como_template(self, repo_url: str) -> None:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        async with await self._get_client() as client:
            res = await client.patch(f"/repos/{self.org}/{repo_name}", json={"is_template": True})
            if res.status_code != 200:
                logger.warning(f"No se pudo marcar {repo_name} como template (HTTP {res.status_code})")

    async def generar_repo_alumno(self, nombre_repo: str, repo_oficial_url: str) -> str:
        # Generar a partir del template original en lugar del repo_oficial
        # para evitar copiar carpetas de otros profesores.
        template = self.template_repo
        
        async with await self._get_client() as client:
            check_res = await client.get(f"/repos/{self.org}/{nombre_repo}")
            if check_res.status_code == 200:
                logger.info(f"El repositorio {self.org}/{nombre_repo} ya existe.")
                return check_res.json().get("clone_url", f"https://github.com/{self.org}/{nombre_repo}.git")
            elif check_res.status_code != 404:
                raise GitHubProvisionError(f"Error comprobando {self.org}/{nombre_repo}: HTTP {check_res.status_code}")

            logger.info(f"Generando {self.org}/{nombre_repo} a partir de {template}...")
            gen_res = await client.post(
                f"/repos/{self.org}/{template}/generate",
                json={
                    "owner": self.org,
                    "name": nombre_repo,
                    "private": True,
                    "include_all_branches": False
                }
            )
            
            if gen_res.status_code in (201, 200):
                return gen_res.json().get("clone_url", f"https://github.com/{self.org}/{nombre_repo}.git")
            else:
                raise GitHubProvisionError(f"Error al aprovisionar {self.org}/{nombre_repo}: HTTP {gen_res.status_code} {gen_res.text}")

    async def crear_commit_archivo(self, repo_url: str, path: str, content: str, message: str) -> str:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        import base64
        
        async with await self._get_client() as client:
            # Check if file exists to get its SHA and current content
            file_res = await client.get(f"/repos/{self.org}/{repo_name}/contents/{path}")
            
            final_content = content
            sha = None
            if file_res.status_code == 200:
                file_data = file_res.json()
                sha = file_data["sha"]
                # Decode existing content and append new content
                existing_content = base64.b64decode(file_data["content"]).decode('utf-8')
                final_content = existing_content + content
                
            encoded_content = base64.b64encode(final_content.encode('utf-8')).decode('utf-8')
            
            data = {
                "message": message,
                "content": encoded_content
            }
            if sha:
                data["sha"] = sha
                
            put_res = await client.put(
                f"/repos/{self.org}/{repo_name}/contents/{path}",
                json=data
            )
            
            if put_res.status_code in (200, 201):
                return put_res.json()["commit"]["sha"]
            else:
                raise GitHubProvisionError(f"Failed to create/update file {path} in {repo_name}: HTTP {put_res.status_code} {put_res.text}")
