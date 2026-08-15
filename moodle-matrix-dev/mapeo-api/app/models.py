"""! @file models.py
@brief Modelos Pydantic para el API de mapeo.

Define las entidades y schemas de validación de datos que utiliza FastAPI
tanto para la base de datos (SQLAlchemy) como para las peticiones/respuestas HTTP.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

from enum import Enum

class MapeoEstado(str, Enum):
    """!
    @brief Estado de la provisión del mapeo de sala y repositorio.
    """
    PENDIENTE_GITHUB = "PENDIENTE_GITHUB"
    ACTIVO = "ACTIVO"

class MapeoBase(BaseModel):
    """!
    @brief Modelo base Pydantic para el Mapeo de Usuario-Curso.
    """
    moodle_user_id: int
    moodle_course_id: int
    repo_url: Optional[str] = None
    official_repo_url: Optional[str] = None
    git_provider: Optional[str] = "github"
    matrix_room_id: Optional[str] = None
    estado: MapeoEstado = MapeoEstado.PENDIENTE_GITHUB
    is_teacher: bool = False
    moodle_username: Optional[str] = None

class MapeoCreate(MapeoBase):
    """!
    @brief Modelo para la creación de un nuevo Mapeo desde Moodle.
    @details Incluye campos adicionales opcionales para facilitar el aprovisionamiento de repositorios.
    """
    moodle_username: str = ""
    moodle_course_shortname: str = ""

class SyncStudent(BaseModel):
    moodle_user_id: int
    moodle_username: str
    is_teacher: bool = False

class SyncRoster(BaseModel):
    moodle_course_id: int
    moodle_course_shortname: str
    students: list[SyncStudent]

class MapeoRead(MapeoBase):
    """!
    @brief Modelo de respuesta HTTP tras la creación o consulta de mapeos.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CursoCreate(BaseModel):
    """!
    @brief Modelo para la provisión del repositorio oficial de un curso.
    """
    moodle_course_shortname: str

class EventoCreate(BaseModel):
    matrix_room_id: str
    commit_sha: str
    tipo_evento: str
    timestamp: str

class EventoRead(EventoCreate):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
