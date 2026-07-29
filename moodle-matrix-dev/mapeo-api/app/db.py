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
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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
    github_repo_url = Column(String, nullable=True)
    matrix_room_id = Column(String, nullable=True)
    estado = Column(String, default="PENDIENTE_GITHUB")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def create_db_and_tables():
    if "sqlite:////data" in DATABASE_URL:
        os.makedirs("/data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
