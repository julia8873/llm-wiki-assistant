import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import MapeoCreate, MapeoRead
from .db import create_db_and_tables, get_session, MapeoDB

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
def create_mapeo(mapeo: MapeoCreate, session: Session = Depends(get_session), token: str = Depends(verify_token)):
    db_mapeo = MapeoDB(**mapeo.dict())
    try:
        session.add(db_mapeo)
        session.commit()
        session.refresh(db_mapeo)
        return db_mapeo
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un mapeo para este usuario y curso."
        )

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
