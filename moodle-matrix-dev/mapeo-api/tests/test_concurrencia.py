import os
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy import create_engine
from app.main import app
from app.db import Base, get_session
from sqlalchemy.orm import sessionmaker

# Configuramos la BD dependiendo del entorno (para el test)
os.environ["MAPEO_API_TOKEN"] = "valid_test_token"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_concurrencia.db")
is_sqlite = TEST_DATABASE_URL.startswith("sqlite")
# Forzamos un timeout muy bajo para asegurar que falle rápido bajo concurrencia simulando alta carga
connect_args = {"check_same_thread": False, "timeout": 0.01} if is_sqlite else {}
engine = create_engine(TEST_DATABASE_URL, connect_args=connect_args)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_session():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def apply_override():
    app.dependency_overrides[get_session] = override_get_session
    yield
    del app.dependency_overrides[get_session]
client = TestClient(app)

def create_mapeo(user_id: int):
    payload = {
        "moodle_user_id": user_id,
        "moodle_course_id": 1,
        "repo_url": f"https://github.com/org/repo-{user_id}",
        "git_provider": "github",
        "matrix_room_id": f"!room{user_id}:localhost"
    }
    # Obtener el token de la app real, o usar el que este configurado
    token = os.getenv("MAPEO_API_TOKEN", "changeme")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = client.post("/mapeos", json=payload, headers=headers)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

def test_concurrencia():
    # Inicializar BD
    Base.metadata.drop_all(bind=engine)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)

    num_threads = 60
    resultados = []

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(create_mapeo, i): i for i in range(num_threads)}
        for future in as_completed(futures):
            res = future.result()
            resultados.append(res)
    
    # Análisis de resultados
    errores_500 = [res for res in resultados if res[0] == 500]
    errores_sql = [res for res in resultados if "database is locked" in res[1].lower() or "operationalerror" in res[1].lower()]
    
    # En SQLite bajo alta concurrencia de escritura, esperamos fallos de OperationalError: database is locked
    if is_sqlite:
        # Assert que se produce el error de bloqueo esperado
        assert len(errores_sql) > 0, f"Se esperaba que SQLite fallara por concurrencia (database is locked), pero no hubieron errores SQL. Resultados: {resultados}"
        print(f"[OK] SQLite falló como se esperaba bajo alta concurrencia: {len(errores_sql)} errores de bloqueo.")
    else:
        # En PostgreSQL, esperamos que TODAS las escrituras concurrentes se completen sin errores 500
        assert len(errores_500) == 0, f"No se esperaban errores de concurrencia en PostgreSQL. Errores: {errores_500}"
        print("[OK] PostgreSQL manejó la concurrencia correctamente, 0 errores.")
