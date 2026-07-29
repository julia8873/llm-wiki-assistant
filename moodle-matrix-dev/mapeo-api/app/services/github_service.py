"""! @file github_service.py
@brief Servicio de aprovisionamiento de repositorios en GitHub.

Contiene la lógica para la creación e idempotencia de los repositorios
de los alumnos generados a partir de un template oficial del curso.
El token de autenticación se lee desde la variable de entorno `GITHUB_PAT`,
que se inyecta automáticamente desde `config/config.yaml` por el script `instalar.sh`.
"""

import os
import httpx
import yaml
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubProvisionError(Exception):
    pass

def load_config():
    """!
    @brief Carga la configuración desde config.yaml.
    @details Busca la configuración en la ruta definida por la variable de entorno
    CONFIG_PATH y si no existe usa un fallback local.
    
    @return dict|None Retorna la configuración como diccionario o None si falla.
    """
    config_path = os.getenv("CONFIG_PATH", "/config/config.yaml")
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback para tests locales
        local_path = os.path.join(os.path.dirname(__file__), "../../../config/config.yaml")
        if os.path.exists(local_path):
            with open(local_path, 'r') as f:
                return yaml.safe_load(f)
        logger.error(f"No se pudo cargar la configuración de {config_path} ni {local_path}")
        return None

async def provisionar_repositorio_alumno(asignatura: str, usuario: str) -> str:
    """!
    @brief Provisiona un repositorio de GitHub para un alumno basado en un template.
    
    @details
    El flujo de aprovisionamiento es idempotente:
    1. Comprueba si el repositorio `[asignatura]-[usuario]` ya existe mediante un GET a la API de GitHub.
    2. Si existe, recupera y retorna la URL de clonación, deteniendo el flujo.
    3. Si no existe (404), invoca el endpoint de generación de repositorios (`/generate`)
       sobre el template oficial `[Asignatura]-Oficial`.
       
    @param asignatura string con el nombre corto o identificador de la asignatura.
    @param usuario string con el nombre de usuario de Moodle.
    @return str URL de clonación (clone_url) del repositorio aprovisionado.
    @exception GitHubProvisionError Cuando hay un problema de autenticación o error en la API.
    """
    config = load_config()
    if not config:
        raise GitHubProvisionError("Configuración no disponible")
    
    org = config['github']['organizacion']
    api_base = config['github']['api_base_url']
    
    # El template es el maestro de la asignatura: <Asignatura>-Oficial
    template_repo = f"{asignatura}-Oficial"
    
    # El repositorio del alumno será: <asignatura>-<usuario>
    student_repo = f"{asignatura}-{usuario}"
    
    pat = (settings.GITHUB_PAT or os.getenv('GITHUB_PAT'))
    if not pat:
        raise GitHubProvisionError("GITHUB_PAT no está configurado en el entorno")

    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient(base_url=api_base, headers=headers) as client:
        # 1. Comprobar si ya existe
        check_res = await client.get(f"/repos/{org}/{student_repo}")
        if check_res.status_code == 200:
            logger.info(f"El repositorio {org}/{student_repo} ya existe.")
            return check_res.json().get("clone_url", f"https://github.com/{org}/{student_repo}.git")
        elif check_res.status_code != 404:
            logger.error(f"Error comprobando repositorio {org}/{student_repo}: {check_res.status_code} {check_res.text}")
            raise GitHubProvisionError(f"Error al verificar repositorio existente: HTTP {check_res.status_code}")

        # 2. No existe, proceder a generarlo
        logger.info(f"Generando {org}/{student_repo} a partir de {template_repo}...")
        gen_res = await client.post(
            f"/repos/{org}/{template_repo}/generate",
            json={
                "owner": org,
                "name": student_repo,
                "private": True,
                "include_all_branches": False
            }
        )
        
        if gen_res.status_code in (201, 200):
            repo_data = gen_res.json()
            logger.info(f"Repositorio creado exitosamente: {repo_data.get('clone_url')}")
            return repo_data.get("clone_url", f"https://github.com/{org}/{student_repo}.git")
        else:
            logger.error(f"Error al generar repositorio {org}/{student_repo}: {gen_res.status_code} {gen_res.text}")
            raise GitHubProvisionError(f"Error al aprovisionar repositorio en GitHub: HTTP {gen_res.status_code}")

async def provisionar_repositorio_oficial(asignatura: str) -> str:
    """!
    @brief Provisiona el repositorio oficial de un curso en GitHub basado en el template base.
    
    @param asignatura string con el nombre corto o identificador de la asignatura.
    @return str URL de clonación (clone_url) del repositorio aprovisionado.
    @exception GitHubProvisionError Cuando hay un problema de autenticación o error en la API.
    """
    config = load_config()
    if not config:
        raise GitHubProvisionError("Configuración no disponible")
    
    org = config['github']['organizacion']
    api_base = config['github']['api_base_url']
    template_repo = config['github']['repo_plantilla']
    
    # El repositorio oficial de la asignatura: <Asignatura>-Oficial
    repo_oficial = f"{asignatura}-Oficial"
    
    pat = (settings.GITHUB_PAT or os.getenv('GITHUB_PAT') or config['github'].get('pat'))
    if not pat:
        raise GitHubProvisionError("GITHUB_PAT no está configurado en el entorno")

    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient(base_url=api_base, headers=headers) as client:
        # 1. Comprobar si ya existe
        check_res = await client.get(f"/repos/{org}/{repo_oficial}")
        if check_res.status_code == 200:
            logger.info(f"El repositorio oficial {org}/{repo_oficial} ya existe.")
            return check_res.json().get("clone_url", f"https://github.com/{org}/{repo_oficial}.git")
        elif check_res.status_code != 404:
            logger.error(f"Error comprobando repositorio {org}/{repo_oficial}: {check_res.status_code} {check_res.text}")
            raise GitHubProvisionError(f"Error al verificar repositorio existente: HTTP {check_res.status_code}")

        # 2. No existe, proceder a generarlo desde repo_plantilla
        logger.info(f"Generando {org}/{repo_oficial} a partir de {template_repo}...")
        gen_res = await client.post(
            f"/repos/{org}/{template_repo}/generate",
            json={
                "owner": org,
                "name": repo_oficial,
                "private": True,
                "include_all_branches": False
            }
        )
        
        if gen_res.status_code in (201, 200, 422):
            repo_data = gen_res.json()
            if gen_res.status_code == 422:
                logger.info("El repositorio ya existe. (422)")
                repo_url = f"https://github.com/{org}/{repo_oficial}.git"
            else:
                logger.info(f"Repositorio oficial creado exitosamente: {repo_data.get('clone_url')}")
                repo_url = repo_data.get("clone_url", f"https://github.com/{org}/{repo_oficial}.git")
                
            # Marcar como template
            logger.info(f"Marcando {org}/{repo_oficial} como template...")
            res_patch = await client.patch(
                f"/repos/{org}/{repo_oficial}",
                json={"is_template": True}
            )
            if res_patch.status_code != 200:
                logger.warning(f"No se pudo marcar como template ({res_patch.status_code})")
                
            return repo_url
        else:
            logger.error(f"Error al generar repositorio oficial {org}/{repo_oficial}: {gen_res.status_code} {gen_res.text}")
            raise GitHubProvisionError(f"Error al aprovisionar repositorio oficial en GitHub: HTTP {gen_res.status_code}")
