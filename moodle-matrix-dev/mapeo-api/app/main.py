"""! @file main.py
@brief Aplicación principal FastAPI para el Mapeo de Salas y Repositorios.

Punto de entrada de la API que coordina Moodle, Matrix (Synapse) y GitHub,
almacenando el estado en una base de datos local de SQLite/MariaDB.
"""

import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hmac
import hashlib
from fastapi import Request
import redis
from rq import Queue, Retry

from .models import MapeoCreate, MapeoRead, MapeoEstado, CursoCreate, EventoCreate, EventoRead, SyncRoster
from .db import create_db_and_tables, get_session, MapeoDB, EventosBotDB
from .services.git import get_git_provider, GitProviderConfigError

app = FastAPI(title="Mapeo API", description="API centralizada para la relación Alumno-Curso-Fork-Sala")

# RQ Setup
redis_conn = redis.Redis(host='redis', port=6379)
sync_queue = Queue('sync-jobs', connection=redis_conn)
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    expected_token = os.getenv("MAPEO_API_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Token no configurado en el servidor")
    
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.on_event("startup")
def on_startup():
    token = os.getenv("MAPEO_API_TOKEN")
    if not token or token in ("default_token", "changeme"):
        raise RuntimeError("FATAL: MAPEO_API_TOKEN no está configurado correctamente. Revisa tu fichero .env.")
    create_db_and_tables()

@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}

@app.post("/mapeos", response_model=MapeoRead, status_code=status.HTTP_201_CREATED)
async def create_mapeo(mapeo: MapeoCreate, session: Session = Depends(get_session), token: str = Depends(verify_token)):
    """!
    @brief Crea un nuevo mapeo y aprovisiona el repositorio en GitHub/GitLab/Gitea.
    @details
    Endpoint llamado por Moodle cuando un alumno accede por primera vez al bloque BdC.
    Se asegura de que no existan mapeos duplicados para el mismo usuario y curso.
    Invoca asíncronamente a `generar_repo_alumno` para interactuar con la API del proveedor de Git.
    
    @param mapeo MapeoCreate Datos enviados desde el bloque de Moodle.
    @param session Session Sesión de la base de datos inyectada por FastAPI.
    @param token str Token de autenticación inyectado por FastAPI.
    @return MapeoRead Entidad creada con el ID, repositorio asignado y estado.
    """
    db_mapeo = MapeoDB(
        moodle_user_id=mapeo.moodle_user_id,
        moodle_course_id=mapeo.moodle_course_id,
        matrix_room_id=mapeo.matrix_room_id,
        estado=MapeoEstado.PENDIENTE_GITHUB,
        is_teacher=1 if mapeo.is_teacher else 0,
        moodle_username=mapeo.moodle_username
    )
    
    try:
        session.add(db_mapeo)
        session.commit()
        session.refresh(db_mapeo)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un mapeo para este usuario y curso."
        )

    # Si se nos provee nombre de usuario y asignatura, aprovisionamos en el Git provider
    if mapeo.moodle_username and mapeo.moodle_course_shortname:
        try:
            provider = get_git_provider()
            nombre_repo = f"{mapeo.moodle_course_shortname}-{mapeo.moodle_username}"
            repo_oficial_url = f"{mapeo.moodle_course_shortname}-Oficial"
            
            from app.services.git import load_config
            cfg = load_config()
            provider_domain = "github.com"
            org = cfg['git']['organizacion']
            
            if mapeo.is_teacher:
                # El profesor usa el repositorio oficial directamente, no creamos un fork
                repo_url = f"https://{provider_domain}/{org}/{repo_oficial_url}.git"
            else:
                repo_url = await provider.generar_repo_alumno(nombre_repo, repo_oficial_url)
            
            # Actualizamos BD con éxito
            db_mapeo.repo_url = repo_url
            db_mapeo.official_repo_url = f"https://{provider_domain}/{org}/{repo_oficial_url}.git"
            db_mapeo.estado = MapeoEstado.ACTIVO
            db_mapeo.is_teacher = 1 if mapeo.is_teacher else 0
            
            provider_name = cfg['git']['proveedor_activo'] if cfg and 'git' in cfg else 'github'
            db_mapeo.git_provider = provider_name
            
            session.commit()
            session.refresh(db_mapeo)
            
            # Encolar el trabajo inicial de sincronización para inyectar material-oficial/ (sólo alumnos)
            # O crear la carpeta para el profesor (sólo profesores)
            if not mapeo.is_teacher:
                job_payload = {
                    "matrix_room_id": db_mapeo.matrix_room_id,
                    "repo_alumno_url": db_mapeo.repo_url,
                    "official_repo_url": db_mapeo.official_repo_url
                }
                sync_queue.enqueue(
                    "sync_worker.tasks.sync_repo_task", 
                    kwargs=job_payload,
                    job_timeout="5m",
                    retry=Retry(max=3, interval=[10, 30, 60])
                )
            else:
                job_payload = {
                    "matrix_room_id": db_mapeo.matrix_room_id,
                    "official_repo_url": db_mapeo.official_repo_url,
                    "moodle_username": mapeo.moodle_username
                }
                sync_queue.enqueue(
                    "sync_worker.tasks.init_teacher_repo_task", 
                    kwargs=job_payload,
                    job_timeout="5m",
                    retry=Retry(max=3, interval=[10, 30, 60])
                )
            
        except Exception as e:
            # Queda guardado como PENDIENTE_GITHUB, pero devolvemos 502 al cliente (Moodle)
            raise HTTPException(
                status_code=502,
                detail=f"Fallo al aprovisionar repositorio Git: {str(e)}"
            )

    return db_mapeo

@app.get("/mapeos", response_model=List[MapeoRead])
def read_mapeos(
    moodle_user_id: Optional[int] = None,
    moodle_course_id: Optional[int] = None,
    matrix_room_id: Optional[str] = None,
    moodle_username: Optional[str] = None,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    print(f"DEBUG: moodle_user_id={moodle_user_id}, moodle_username={moodle_username}")
    query = session.query(MapeoDB)
    if moodle_user_id is not None:
        query = query.filter(MapeoDB.moodle_user_id == moodle_user_id)
    if moodle_course_id is not None:
        query = query.filter(MapeoDB.moodle_course_id == moodle_course_id)
    if matrix_room_id is not None:
        query = query.filter(MapeoDB.matrix_room_id == matrix_room_id)
    if moodle_username is not None:
        query = query.filter(MapeoDB.moodle_username == moodle_username)
    
    results = query.all()
    
    if not results and (moodle_user_id is not None or moodle_course_id is not None or matrix_room_id is not None):
        raise HTTPException(status_code=404, detail="Mapeo no encontrado")
        
    return results

@app.post("/mapeos/sync-roster", status_code=status.HTTP_200_OK)
def sync_roster(
    roster: SyncRoster,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Sincroniza la lista de alumnos de un curso."""
    course_id = roster.moodle_course_id
    
    for student in roster.students:
        # Check si ya existe
        existing = session.query(MapeoDB).filter(
            MapeoDB.moodle_user_id == student.moodle_user_id,
            MapeoDB.moodle_course_id == course_id
        ).first()
        
        if not existing:
            new_mapeo = MapeoDB(
                moodle_user_id=student.moodle_user_id,
                moodle_course_id=course_id,
                estado=MapeoEstado.PENDIENTE_GITHUB,
                is_teacher=1 if student.is_teacher else 0,
                moodle_username=student.moodle_username
            )
            session.add(new_mapeo)
    
    session.commit()
    return {"status": "ok"}

@app.get("/mapeos/by-room/{matrix_room_id}", response_model=MapeoRead)
def get_by_room(matrix_room_id: str, session: Session = Depends(get_session), token: str = Depends(verify_token)):
    result = session.query(MapeoDB).filter(MapeoDB.matrix_room_id == matrix_room_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Mapeo no encontrado para esta sala")
    return result

@app.post("/cursos", status_code=status.HTTP_201_CREATED)
async def create_curso(curso: CursoCreate, token: str = Depends(verify_token)):
    """!
    @brief Aprovisiona la plantilla oficial del curso en el proveedor Git.
    @details
    Endpoint llamado por Moodle al crear un curso nuevo.
    """
    try:
        provider = get_git_provider()
        # Usamos BdC-template como identificador del template oficial
        repo_url = await provider.crear_repo_oficial(curso.moodle_course_shortname, template_id="BdC-template")
        # Marcamos como template para que los alumnos lo puedan copiar limpiamente
        await provider.marcar_como_template(repo_url)
        return {"status": "ok", "repo_url": repo_url}
    except Exception as e:
        import logging
        logging.error("Exception in create_curso", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Fallo al aprovisionar plantilla oficial en el proveedor Git: {str(e)}"
        )


@app.post("/sync/oficial-updated")
async def sync_webhook(request: Request, session: Session = Depends(get_session)):
    # 1. Verificar firma HMAC
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    signature_header = request.headers.get("x-hub-signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    payload = await request.body()
    hash_obj = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256)
    expected_signature = "sha256=" + hash_obj.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Procesar payload
    data = await request.json()
    
    # Solo procesamos push a la rama por defecto
    if "repository" not in data or "ref" not in data:
        return {"status": "ignored", "reason": "Not a push event to repository"}

    default_branch = data["repository"].get("default_branch", "main")
    if data["ref"] != f"refs/heads/{default_branch}":
        return {"status": "ignored", "reason": f"Not pushing to default branch {default_branch}"}

    official_repo_url = data["repository"].get("clone_url")
    if not official_repo_url:
        raise HTTPException(status_code=400, detail="No clone_url in payload")

    # 3. Buscar todos los alumnos que referencian este repositorio oficial
    alumnos = session.query(MapeoDB).filter(
        MapeoDB.official_repo_url == official_repo_url,
        MapeoDB.is_teacher == 0
    ).all()

    if not alumnos:
        return {"status": "ignored", "reason": "No mapped students found for this official repo"}

    # 4. Encolar los jobs
    enqueued = 0
    for alumno in alumnos:
        if alumno.repo_url and alumno.matrix_room_id:
            job_payload = {
                "matrix_room_id": alumno.matrix_room_id,
                "repo_alumno_url": alumno.repo_url,
                "official_repo_url": official_repo_url
            }
            # The function string is the module path to the task inside sync-worker
            sync_queue.enqueue(
                "sync_worker.tasks.sync_repo_task", 
                kwargs=job_payload,
                job_timeout="5m",
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            enqueued += 1

    return {"status": "ok", "enqueued_jobs": enqueued}


@app.post("/eventos", response_model=EventoRead, status_code=status.HTTP_201_CREATED)
async def create_evento(evento: EventoCreate, session: Session = Depends(get_session), token: str = Depends(verify_token)):
    db_evento = EventosBotDB(
        matrix_room_id=evento.matrix_room_id,
        commit_sha=evento.commit_sha,
        tipo_evento=evento.tipo_evento,
        timestamp=evento.timestamp
    )
    
    try:
        session.add(db_evento)
        session.commit()
        session.refresh(db_evento)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="El evento con este commit_sha ya existe."
        )

    return db_evento


@app.get("/eventos-recientes", response_model=List[EventoRead])
def read_eventos_recientes(
    limit: int = 100,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Devuelve los eventos más recientes."""
    results = session.query(EventosBotDB).order_by(EventosBotDB.created_at.desc()).limit(limit).all()
    return results
