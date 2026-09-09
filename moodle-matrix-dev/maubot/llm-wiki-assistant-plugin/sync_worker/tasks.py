"""! @file tasks.py
@brief Tareas asíncronas encoladas en Redis/RQ para la sincronización de repositorios.
"""

import os
import asyncio
import logging
import httpx
from git_utils import asegurar_repo_local, run_git_command, asegurar_estructura_okf, distributed_repo_lock
from shared_pkg.okf_contract import COMMIT_MSG_SYNC, PATH_LOG_INTERACCIONES, COMMIT_MSG_LOG
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mixins.mapeo_client import MapeoClient

def get_mapeo_client():
    token = os.environ.get("MAPEO_API_TOKEN", "")
    url = os.environ.get("MAPEO_API_URL", "http://mapeo-api:8000")
    return MapeoClient(url, token)

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
        async with distributed_repo_lock(destino_local):
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
                "git archive upstream/main | tar -x --exclude='logs' --exclude='logs/*' --exclude='bitacora' --exclude='bitacora/*' --exclude='profesores/*/logs' --exclude='profesores/*/logs/*' --exclude='profesores/*/bitacora' --exclude='profesores/*/bitacora/*' --exclude='profesores/*/okf/log.md' -C material-oficial/",
                cwd=destino_local,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out_tar, err_tar = await process_tar.communicate()
            if process_tar.returncode != 0:
                raise RuntimeError(f"Error extrayendo upstream a material-oficial: {err_tar.decode()}")

            # 4.5. Si el estudiante no tiene AGENTS.md en la raíz, inicializar su repositorio base
            if not os.path.exists(os.path.join(destino_local, "AGENTS.md")):
                logger.info("Inicializando raíz del repositorio del estudiante con la plantilla base.")
                import shutil
                # Copiar archivos raíz del template (AGENTS.md, README.md, etc.) desde material-oficial
                material_dir = os.path.join(destino_local, "material-oficial")
                for item in os.listdir(material_dir):
                    if item not in [".git", "profesores", "material-oficial"]:
                        s = os.path.join(material_dir, item)
                        d = os.path.join(destino_local, item)
                        if not os.path.exists(d):
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)
                
                # Asegurar carpetas clave por si Git las ignoró al estar vacías y forzar su trackeo
                asegurar_estructura_okf(destino_local)
                
                # Añadir los nuevos archivos a Git
                await run_git_command('add', '.', cwd=destino_local)

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
            
            code, out, err = await run_git_command('commit', '-m', COMMIT_MSG_SYNC, cwd=destino_local)
            if code != 0:
                logger.info("Nada que commitear o no hay cambios.")
                return

            # 7. Git push
            code, out, err = await run_git_command('push', 'origin', 'main', cwd=destino_local)
            if code != 0:
                raise RuntimeError(f"Error en git push: {err}")
                
            code, out, err = await run_git_command('rev-parse', 'HEAD', cwd=destino_local)
            commit_sha = out.strip()
            
            # Post evento
            try:
                client = get_mapeo_client()
                await client.post_evento(
                    matrix_room_id=matrix_room_id,
                    commit_sha=commit_sha,
                    tipo_evento="SYNC",
                    timestamp_str=datetime.datetime.utcnow().isoformat() + "Z"
                )
            except Exception as e:
                logger.error(f"Error posteando evento SYNC a mapeo-api: {e}")

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
        async with distributed_repo_lock(destino_local):
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
            
            # Creamos los directorios básicos mediante la función unificada
            asegurar_estructura_okf(teacher_dir)
            
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

def log_interaccion_unificada_task(matrix_room_id: str, repo_alumno_url: str, official_repo_url: str, log_data: dict):
    """!
    @brief Tarea síncrona que envuelve el loop asíncrono para registrar una interacción unificada (Fase 11.1).
    """
    asyncio.run(_async_log_interaccion_unificada_task(matrix_room_id, repo_alumno_url, official_repo_url, log_data))

async def _async_log_interaccion_unificada_task(matrix_room_id: str, repo_alumno_url: str, official_repo_url: str, log_data: dict):
    import urllib.parse
    import json
    import datetime
    import hashlib
    
    safe_name = urllib.parse.quote_plus(repo_alumno_url)
    destino_local = f"/tmp/llm_wiki_repos/{safe_name}"
    
    logger.info(f"Iniciando log_interaccion_unificada_task para la sala {matrix_room_id}")

    try:
        async with distributed_repo_lock(destino_local):
            await asegurar_repo_local(repo_alumno_url, official_repo_url, destino_local)
            
            interacciones_dir = os.path.join(destino_local, PATH_LOG_INTERACCIONES)
            os.makedirs(interacciones_dir, exist_ok=True)
            
            # Formato de archivo: logs/interacciones/YYYY-MM-DD.jsonl
            # Extract timestamp directly from log_data or use current
            iso_timestamp = log_data.get("timestamp", datetime.datetime.utcnow().isoformat() + "Z")
            try:
                dt = datetime.datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
                fecha = dt.strftime("%Y-%m-%d")
            except Exception:
                fecha = datetime.datetime.utcnow().strftime("%Y-%m-%d")

            log_path = os.path.join(destino_local, PATH_LOG_INTERACCIONES, f"{fecha}.jsonl")
            
            # --- PII Guard Integration ---
            from pii_guard import pseudonymize_text, send_pii_to_vault
            
            # Use same interaction_id generation as metrics-api
            interaction_id = hashlib.sha256(iso_timestamp.encode()).hexdigest()[:16]
            student_matrix_id = log_data.get("sender", matrix_room_id) # sender might be the user id, fallback to room id
            
            all_mappings = []
            
            if "mensaje_alumno" in log_data and log_data["mensaje_alumno"]:
                anon_msg, mappings = pseudonymize_text(log_data["mensaje_alumno"])
                log_data["mensaje_alumno"] = anon_msg
                all_mappings.extend(mappings)
                
            if "respuesta_bot" in log_data and log_data["respuesta_bot"]:
                anon_resp, mappings = pseudonymize_text(log_data["respuesta_bot"])
                log_data["respuesta_bot"] = anon_resp
                all_mappings.extend(mappings)
                
            if all_mappings:
                # This will raise exception and abort sync if it fails
                send_pii_to_vault(student_matrix_id, interaction_id, all_mappings)
            # ---------------------------
            
            # Serializar la entrada para hacer el append
            line_str = json.dumps(log_data, ensure_ascii=False)
            
            # Idempotencia: comprobar si la línea/hash ya existe en este fichero del working tree
            line_hash = hashlib.sha256(line_str.encode('utf-8')).hexdigest()
            already_logged = False
            
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if hashlib.sha256(line.strip().encode('utf-8')).hexdigest() == line_hash:
                            already_logged = True
                            break
            
            if not already_logged:
                # Escribir y comitear
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line_str + "\n")
                
                await run_git_command('add', f'{PATH_LOG_INTERACCIONES}/{fecha}.jsonl', cwd=destino_local)
                code, out, err = await run_git_command('commit', '-m', f'{COMMIT_MSG_LOG} {iso_timestamp}', cwd=destino_local)
                if code != 0:
                    logger.warning(f"Git commit omitido (sin cambios): {err}")
            else:
                logger.info(f"Entrada de log ya presente (idempotencia). Se omite escritura y commit local.")

            # Hacer push independientemente de si se escribió ahora o ya estaba en el tree local
            code, out, err = await run_git_command('push', 'origin', 'main', cwd=destino_local)
            if code != 0:
                raise RuntimeError(f"Error en git push de logs: {err}")
                
            code, out, err = await run_git_command('rev-parse', 'HEAD', cwd=destino_local)
            commit_sha = out.strip()
            
            # Escribir payload con commit_sha en un buffer local para backfill (fuera de git)
            backfill_payload = log_data.copy()
            backfill_payload["commit_sha"] = commit_sha
            backfill_payload["matrix_room_id"] = matrix_room_id
            backfill_path = os.path.join(destino_local, ".backfill.jsonl")
            with open(backfill_path, "a", encoding="utf-8") as bf:
                bf.write(json.dumps(backfill_payload, ensure_ascii=False) + "\n")

            # Post evento
            try:
                client = get_mapeo_client()
                await client.post_evento(
                    matrix_room_id=matrix_room_id,
                    commit_sha=commit_sha,
                    tipo_evento="INTERACTION",
                    timestamp_str=datetime.datetime.utcnow().isoformat() + "Z"
                )
            except Exception as e:
                logger.error(f"Error posteando evento INTERACTION a mapeo-api: {e}")
                
            logger.info("Log de interacciones completado exitosamente.")
            
    except Exception as e:
        logger.error(f"Fallo en log_interaccion_unificada_task: {e}")
        raise e
