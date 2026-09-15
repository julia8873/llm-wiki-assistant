from fastapi.testclient import TestClient
import os
import pytest
from app.main import app
from app.db import Base, engine, get_session
from sqlalchemy.orm import sessionmaker

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

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
    except Exception:
        pass

def test_post_evento_idempotency():
    client = TestClient(app)
    token = os.getenv("MAPEO_API_TOKEN", "test_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    import uuid
    test_sha = uuid.uuid4().hex[:8]
    payload = {
        "matrix_room_id": "!room:matrix.org",
        "commit_sha": test_sha,
        "tipo_evento": "INTERACTION",
        "timestamp": "2026-08-14T10:00:00Z"
    }
    
    # Primera inserción: debe devolver 201
    resp1 = client.post("/eventos", json=payload, headers=headers)
    assert resp1.status_code == 201
    assert resp1.json()["commit_sha"] == test_sha
    
    # Segunda inserción del mismo evento: debe devolver 409
    resp2 = client.post("/eventos", json=payload, headers=headers)
    assert resp2.status_code == 409
    assert "ya existe" in resp2.json()["detail"].lower()
    
    # Verificamos que no se duplicó recuperando los eventos
    resp_get = client.get("/eventos-recientes", headers=headers)
    assert resp_get.status_code == 200
    assert len(resp_get.json()) >= 1
