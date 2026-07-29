import pytest
import respx
import httpx
from unittest.mock import patch
from app.core.config import Settings
from app.services.github_service import provisionar_repositorio_alumno, GitHubProvisionError

# Fixture de configuración mockeada
@pytest.fixture
def mock_config():
    return {
        "github": {
            "organizacion": "test-org",
            "api_base_url": "https://api.github.com"
        }
    }

@pytest.mark.asyncio
@respx.mock
@patch('app.services.github_service.load_config')
@patch('os.getenv')
async def test_provisionar_repositorio_nuevo_exito(mock_getenv, mock_load_config, mock_config):
    # Configuración mock
    mock_load_config.return_value = mock_config
    mock_getenv.return_value = "fake-pat"

    asignatura = "Math101"
    usuario = "studentA"
    
    # 1. Mock GET -> 404 (no existe)
    respx.get(f"https://api.github.com/repos/test-org/Math101-studentA").respond(status_code=404)
    
    # 2. Mock POST /generate -> 201 (creado exitosamente)
    respx.post(f"https://api.github.com/repos/test-org/Math101-Oficial/generate").respond(
        status_code=201,
        json={"clone_url": "https://github.com/test-org/Math101-studentA.git"}
    )
    
    url = await provisionar_repositorio_alumno(asignatura, usuario)
    assert url == "https://github.com/test-org/Math101-studentA.git"

@pytest.mark.asyncio
@respx.mock
@patch('app.services.github_service.load_config')
@patch('os.getenv')
async def test_provisionar_repositorio_existente_reutilizacion(mock_getenv, mock_load_config, mock_config):
    # Configuración mock
    mock_load_config.return_value = mock_config
    mock_getenv.return_value = "fake-pat"

    asignatura = "Math101"
    usuario = "studentB"
    
    # 1. Mock GET -> 200 (ya existe)
    respx.get(f"https://api.github.com/repos/test-org/Math101-studentB").respond(
        status_code=200,
        json={"clone_url": "https://github.com/test-org/Math101-studentB.git"}
    )
    
    url = await provisionar_repositorio_alumno(asignatura, usuario)
    assert url == "https://github.com/test-org/Math101-studentB.git"

@pytest.mark.asyncio
@respx.mock
@patch('app.services.github_service.load_config')
@patch('os.getenv')
async def test_provisionar_repositorio_fallo_controlado(mock_getenv, mock_load_config, mock_config):
    # Configuración mock
    mock_load_config.return_value = mock_config
    mock_getenv.return_value = "fake-pat"

    asignatura = "Math101"
    usuario = "studentC"
    
    # 1. Mock GET -> 500 (falla la API de GitHub)
    respx.get(f"https://api.github.com/repos/test-org/Math101-studentC").respond(status_code=500)
    
    with pytest.raises(GitHubProvisionError) as exc_info:
        await provisionar_repositorio_alumno(asignatura, usuario)
    
    assert "HTTP 500" in str(exc_info.value)

@pytest.mark.asyncio
@respx.mock
@patch('app.services.github_service.load_config')
@patch('app.services.github_service.os.getenv', return_value=None)
async def test_provisionar_repositorio_usa_settings_para_pat(mock_getenv, mock_load_config, mock_config):
    mock_load_config.return_value = mock_config

    asignatura = "Math101"
    usuario = "studentD"

    respx.get(f"https://api.github.com/repos/test-org/Math101-studentD").respond(status_code=404)
    respx.post(f"https://api.github.com/repos/test-org/Math101-Oficial/generate").respond(
        status_code=201,
        json={"clone_url": "https://github.com/test-org/Math101-studentD.git"}
    )

    with patch('app.services.github_service.settings', Settings(GITHUB_PAT="settings-pat"), create=True):
        url = await provisionar_repositorio_alumno(asignatura, usuario)

    assert url == "https://github.com/test-org/Math101-studentD.git"
