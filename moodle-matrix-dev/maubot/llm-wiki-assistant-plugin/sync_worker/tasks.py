"""! @file tasks.py
@brief Tareas asíncronas encoladas en Redis/RQ para la sincronización de repositorios.
"""

import os
import asyncio
import logging
import httpx
from git_utils import asegurar_repo_local, run_git_command

logger = logging.getLogger(__name__)

def sync_repo_task(matrix_room_id: str, repo_alumno_url: str, official_repo_url: str):
    """!
    @brief Tarea síncrona que envuelve el loop asíncrono para ejecutar el job de sync.
    """
    asyncio.run(_async_sync_repo_task(matrix_room_id, repo_alumno_url, official_repo_url))

async def _async_sync_repo_task(matrix_room_id: str, repo_alumno_url: str, official_repo_url: str):
    import urllib.parse
    safe_name = urllib.parse.quote_plus(repo_alumno_url)
    destino_local = f"/tmp/llm_wiki_repos/{safe_name}"
    
    logger.info(f"Iniciando sync_repo_task para {matrix_room_id}")

    try:
        # 1. Asegurar repositorio
        await asegurar_repo_local(repo_alumno_url, official_repo_url, destino_local)
        
        # 2. Fetch de upstream (por si acaso asegurar_repo_local no lo hizo con upstream)
        code, out, err = await run_git_command('fetch', 'upstream', cwd=destino_local)
        if code != 0:
            raise RuntimeError(f"Error en git fetch upstream: {err}")

        # 3. Limpiar carpeta material-oficial y crearla nueva
        process_clean = await asyncio.create_subprocess_shell(
            "rm -rf material-oficial && mkdir -p material-oficial",
            cwd=destino_local
        )
        await process_clean.communicate()
        
        # 4. Extraer TODO el repositorio upstream en la carpeta material-oficial
        process_tar = await asyncio.create_subprocess_shell(
            "git archive upstream/main | tar -x --exclude='logs' -C material-oficial/",
            cwd=destino_local,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out_tar, err_tar = await process_tar.communicate()
        if process_tar.returncode != 0:
            raise RuntimeError(f"Error extrayendo upstream a material-oficial: {err_tar.decode()}")

        # 5. Añadir entrada al log del alumno
        import datetime
        log_path = os.path.join(destino_local, "logs", "log.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] Sincronización automática de materiales del profesor completada.\n")

        # 6. Git add y commit
        code, out, err = await run_git_command('add', 'material-oficial/', cwd=destino_local)
        code, out, err = await run_git_command('add', 'logs/log.txt', cwd=destino_local)
        
        code, out, err = await run_git_command('commit', '-m', 'Sincronización automática completa de material oficial', cwd=destino_local)
        if code != 0:
            logger.info("Nada que commitear o no hay cambios.")
            return

        # 7. Git push
        code, out, err = await run_git_command('push', 'origin', 'main', cwd=destino_local)
        if code != 0:
            raise RuntimeError(f"Error en git push: {err}")

        logger.info(f"Sync completado con éxito para {matrix_room_id}")

    except Exception as e:
        logger.error(f"Fallo en sync_repo_task: {e}")
        raise e

def init_teacher_repo_task(matrix_room_id: str, official_repo_url: str, moodle_username: str):
    """!
    @brief Tarea síncrona que envuelve el loop asíncrono para inicializar la carpeta del profesor.
    """
    asyncio.run(_async_init_teacher_repo_task(matrix_room_id, official_repo_url, moodle_username))

async def _async_init_teacher_repo_task(matrix_room_id: str, official_repo_url: str, moodle_username: str):
    import urllib.parse
    safe_name = urllib.parse.quote_plus(official_repo_url)
    destino_local = f"/tmp/llm_wiki_repos/{safe_name}"
    
    logger.info(f"Iniciando init_teacher_repo_task para {moodle_username} en {matrix_room_id}")

    try:
        # 1. Asegurar repositorio oficial (sólo clonar origin)
        # Usamos la misma función pero pasando el repo oficial como principal y sin upstream
        await asegurar_repo_local(official_repo_url, "", destino_local)
        
        # 2. Comprobar si la carpeta ya existe
        teacher_dir = os.path.join(destino_local, "profesores", moodle_username)
        if os.path.exists(teacher_dir):
            logger.info(f"La carpeta del profesor {moodle_username} ya existe. Omitiendo inicialización.")
            return

        # 3. Crear estructura imitando el repositorio raíz
        os.makedirs(teacher_dir, exist_ok=True)
        
        # Creamos los directorios básicos si no los queremos copiar dinámicamente
        for d in ["raw", "conceptos", "bitacora"]:
            d_path = os.path.join(teacher_dir, d)
            os.makedirs(d_path, exist_ok=True)
            with open(os.path.join(d_path, ".gitkeep"), "w") as f:
                f.write("")
        
        # Copiar AGENTS.md si existe en la raíz
        agents_src = os.path.join(destino_local, "AGENTS.md")
        if os.path.exists(agents_src):
            import shutil
            shutil.copy2(agents_src, os.path.join(teacher_dir, "AGENTS.md"))

        # 4. Git add y commit
        code, out, err = await run_git_command('add', f'profesores/{moodle_username}/', cwd=destino_local)
        code, out, err = await run_git_command('commit', '-m', f'Inicialización de carpeta para profesor {moodle_username}', cwd=destino_local)
        if code != 0:
            logger.info("Nada que commitear o no hay cambios.")
            return

        # 5. Git push
        code, out, err = await run_git_command('push', 'origin', 'main', cwd=destino_local)
        if code != 0:
            raise RuntimeError(f"Error en git push: {err}")

        logger.info(f"Inicialización de carpeta de profesor completada con éxito para {moodle_username}")

    except Exception as e:
        logger.error(f"Fallo en init_teacher_repo_task: {e}")
        raise e
