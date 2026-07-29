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

from .models import MapeoCreate, MapeoRead, MapeoEstado, CursoCreate
from .db import create_db_and_tables, get_session, MapeoDB
from .services.github_service import provisionar_repositorio_alumno, provisionar_repositorio_oficial, GitHubProvisionError

app = FastAPI(title="Mapeo API", description="API centralizada para la relación Alumno-Curso-Fork-Sala")

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
    @brief Crea un nuevo mapeo y aprovisiona el repositorio en GitHub.
    @details
    Endpoint llamado por Moodle cuando un alumno accede por primera vez al bloque BdC.
    Se asegura de que no existan mapeos duplicados para el mismo usuario y curso.
    Invoca asíncronamente a `provisionar_repositorio_alumno` para interactuar con la API de GitHub.
    
    @param mapeo MapeoCreate Datos enviados desde el bloque de Moodle.
    @param session Session Sesión de la base de datos inyectada por FastAPI.
    @param token str Token de autenticación inyectado por FastAPI.
    @return MapeoRead Entidad creada con el ID, repositorio asignado y estado.
    """
    db_mapeo = MapeoDB(
        moodle_user_id=mapeo.moodle_user_id,
        moodle_course_id=mapeo.moodle_course_id,
        matrix_room_id=mapeo.matrix_room_id,
        estado=MapeoEstado.PENDIENTE_GITHUB
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

    # Si se nos provee nombre de usuario y asignatura, aprovisionamos GitHub
    if mapeo.moodle_username and mapeo.moodle_course_shortname:
        try:
            repo_url = await provisionar_repositorio_alumno(
                asignatura=mapeo.moodle_course_shortname,
                usuario=mapeo.moodle_username
            )
            # Actualizamos BD con éxito
            db_mapeo.github_repo_url = repo_url
            db_mapeo.estado = MapeoEstado.ACTIVO
            session.commit()
            session.refresh(db_mapeo)
        except GitHubProvisionError as e:
            # Queda guardado como PENDIENTE_GITHUB, pero devolvemos 502 al cliente (Moodle)
            raise HTTPException(
                status_code=502,
                detail=f"Fallo al aprovisionar GitHub: {str(e)}"
            )

    return db_mapeo

@app.get("/mapeos", response_model=List[MapeoRead])
def read_mapeos(
    moodle_user_id: Optional[int] = None,
    moodle_course_id: Optional[int] = None,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    query = session.query(MapeoDB)
    if moodle_user_id is not None:
        query = query.filter(MapeoDB.moodle_user_id == moodle_user_id)
    if moodle_course_id is not None:
        query = query.filter(MapeoDB.moodle_course_id == moodle_course_id)
    
    results = query.all()
    
    if moodle_user_id is not None and moodle_course_id is not None and not results:
        raise HTTPException(status_code=404, detail="Mapeo no encontrado")
        
    return results

@app.get("/mapeos/by-room/{matrix_room_id}", response_model=MapeoRead)
def get_by_room(matrix_room_id: str, session: Session = Depends(get_session), token: str = Depends(verify_token)):
    result = session.query(MapeoDB).filter(MapeoDB.matrix_room_id == matrix_room_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Mapeo no encontrado para esta sala")
    return result

@app.post("/cursos", status_code=status.HTTP_201_CREATED)
async def create_curso(curso: CursoCreate, token: str = Depends(verify_token)):
    """!
    @brief Aprovisiona la plantilla oficial del curso en GitHub.
    @details
    Endpoint llamado por Moodle al crear un curso nuevo.
    """
    try:
        repo_url = await provisionar_repositorio_oficial(curso.moodle_course_shortname)
        return {"status": "ok", "github_repo_url": repo_url}
    except GitHubProvisionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Fallo al aprovisionar plantilla oficial en GitHub: {str(e)}"
        )
