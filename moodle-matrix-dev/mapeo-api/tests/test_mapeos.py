import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_session, Base

engine = create_engine(
    "sqlite://", 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session_override():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_session] = get_session_override

@pytest.fixture(name="client")
def client_fixture():
    os.environ["MAPEO_API_TOKEN"] = "test_token"
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    yield client
    Base.metadata.drop_all(bind=engine)

def test_create_and_read_mapeo(client: TestClient):
    headers = {"Authorization": "Bearer test_token"}
    
    response = client.post("/mapeos", json={
        "moodle_user_id": 10,
        "moodle_course_id": 5,
        "repo_url": "https://github.com/user/fork1",
        "matrix_room_id": "!room1:matrix.org"
    }, headers=headers)
    assert response.status_code == 201
    
    response = client.get("/mapeos?moodle_user_id=10&moodle_course_id=5", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["matrix_room_id"] == "!room1:matrix.org"
    
def test_read_nonexistent_returns_404(client: TestClient):
    headers = {"Authorization": "Bearer test_token"}
    response = client.get("/mapeos?moodle_user_id=99&moodle_course_id=99", headers=headers)
    assert response.status_code == 404

def test_same_user_different_courses(client: TestClient):
    headers = {"Authorization": "Bearer test_token"}
    client.post("/mapeos", json={
        "moodle_user_id": 15,
        "moodle_course_id": 1,
        "repo_url": "url1",
        "matrix_room_id": "room1"
    }, headers=headers)
    
    response = client.post("/mapeos", json={
        "moodle_user_id": 15,
        "moodle_course_id": 2,
        "repo_url": "url2",
        "matrix_room_id": "room2"
    }, headers=headers)
    assert response.status_code == 201
    
    response = client.post("/mapeos", json={
        "moodle_user_id": 15,
        "moodle_course_id": 2,
        "repo_url": "url3",
        "matrix_room_id": "room3"
    }, headers=headers)
    assert response.status_code == 409
