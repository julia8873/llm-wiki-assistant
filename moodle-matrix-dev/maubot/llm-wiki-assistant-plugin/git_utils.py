"""! @file git_utils.py
@brief Utilidades compartidas para operaciones de Git.
"""

import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def run_git_command(*args, cwd: str) -> tuple[int, str, str]:
    """!
    @brief Ejecuta un comando git de forma asíncrona.
    """
    process = await asyncio.create_subprocess_exec(
        'git', *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()

async def asegurar_repo_local(repo_alumno_url: str, official_repo_url: Optional[str], destino_local: str) -> None:
    """!
    @brief Asegura que el repositorio local exista, esté actualizado y tenga configurado el remote upstream.
    
    @param repo_alumno_url URL del repositorio del alumno (origin).
    @param official_repo_url URL del repositorio oficial (upstream). Puede ser None.
    @param destino_local Ruta local donde debe alojarse el repositorio.
    """
    pat = os.getenv("GITHUB_PAT")
    
    # 1. Asegurar clonado
    if not os.path.exists(destino_local):
        if pat:
            # Inyectar credenciales en la URL si es http/https
            if repo_alumno_url.startswith("https://"):
                auth_url = repo_alumno_url.replace("https://", f"https://oauth2:{pat}@")
            else:
                auth_url = repo_alumno_url
        else:
            auth_url = repo_alumno_url

        logger.info(f"Clonando {repo_alumno_url} en {destino_local}")
        parent_dir = os.path.dirname(destino_local)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Git clone
        process = await asyncio.create_subprocess_exec(
            'git', 'clone', auth_url, os.path.basename(destino_local),
            cwd=parent_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Error al clonar repositorio: {stderr.decode()}")
            
    else:
        logger.info(f"Repositorio ya existe en {destino_local}, haciendo fetch/pull")
        code, out, err = await run_git_command('fetch', 'origin', cwd=destino_local)
        if code != 0:
            logger.warning(f"Error en fetch origin: {err}")
            
        code, out, err = await run_git_command('reset', '--hard', 'origin/main', cwd=destino_local)
        if code != 0:
            logger.warning(f"Error en reset origin/main: {err}")

    # Set author for bot commits (alway ensure it's set)
    await run_git_command('config', 'user.name', 'LLM Wiki Assistant', cwd=destino_local)
    await run_git_command('config', 'user.email', 'bot@llm-wiki', cwd=destino_local)

    # 2. Configurar remote upstream
    if official_repo_url:
        if pat and official_repo_url.startswith("https://"):
            official_auth_url = official_repo_url.replace("https://", f"https://oauth2:{pat}@")
        else:
            official_auth_url = official_repo_url

        # Check if upstream exists
        code, out, err = await run_git_command('remote', 'get-url', 'upstream', cwd=destino_local)
        if code == 0:
            # Upstream exists, update URL
            if out.strip() != official_auth_url:
                await run_git_command('remote', 'set-url', 'upstream', official_auth_url, cwd=destino_local)
        else:
            # Upstream doesn't exist, add it
            await run_git_command('remote', 'add', 'upstream', official_auth_url, cwd=destino_local)
