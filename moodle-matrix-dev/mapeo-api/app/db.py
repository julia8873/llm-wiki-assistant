"""! @file db.py
@brief Configuración de la base de datos (SQLAlchemy).

Se encarga de la conexión a la base de datos local (SQLite por defecto)
y de la definición del ORM para la tabla de mapeos.
"""

from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/mapeos.db")
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class MapeoDB(Base):
    """!
    @brief Modelo ORM para la tabla 'mapeos'.
    @details Mantiene la relación entre un estudiante de Moodle (por su curso) y
    sus correspondientes recursos externos (GitHub y Matrix).
    """
    __tablename__ = "mapeos"
    __table_args__ = (
        UniqueConstraint("moodle_user_id", "moodle_course_id", name="uq_user_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    moodle_user_id = Column(Integer, nullable=False)
    moodle_course_id = Column(Integer, nullable=False)
    repo_url = Column(String, nullable=True)
    official_repo_url = Column(String, nullable=True)
    git_provider = Column(String, nullable=False, default="github")
    matrix_room_id = Column(String, nullable=True)
    estado = Column(String, default="PENDIENTE_GITHUB")
    is_teacher = Column(Integer, default=0)
    moodle_username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EventosBotDB(Base):
    """!
    @brief Modelo ORM para la tabla 'eventos_bot'.
    @details Registra los eventos que el bot produce y envía al feed.
    """
    __tablename__ = "eventos_bot"

    id = Column(Integer, primary_key=True, index=True)
    matrix_room_id = Column(String, nullable=False, index=True)
    commit_sha = Column(String, nullable=False, unique=True, index=True)
    tipo_evento = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_db_and_tables():
    if "sqlite:////data" in DATABASE_URL:
        os.makedirs("/data", exist_ok=True)
    # Base.metadata.create_all(bind=engine)  # Removed in favor of Alembic

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
