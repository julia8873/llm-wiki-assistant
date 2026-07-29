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
    github_repo_url: Optional[str] = None
    matrix_room_id: Optional[str] = None
    estado: MapeoEstado = MapeoEstado.PENDIENTE_GITHUB

class MapeoCreate(MapeoBase):
    """!
    @brief Modelo para la creación de un nuevo Mapeo desde Moodle.
    @details Incluye campos adicionales opcionales para facilitar el aprovisionamiento de repositorios.
    """
    moodle_username: str = ""
    moodle_course_shortname: str = ""

class MapeoRead(MapeoBase):
    """!
    @brief Modelo de respuesta HTTP tras la creación o consulta de mapeos.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
