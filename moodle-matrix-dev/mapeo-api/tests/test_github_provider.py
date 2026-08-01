import pytest
import respx
import httpx
import os
from unittest.mock import patch
from app.core.config import Settings
from app.services.git.github_provider import GitHubProvider, GitHubProvisionError

@pytest.fixture
def base_config():
    return {
        'git': {
            'organizacion': 'test-org',
            'repo_plantilla': 'test-template',
            'github': {
                'api_base_url': 'https://api.github.com',
                'pat': 'test-pat-123',
                'pat_env_var': 'GITHUB_PAT'
            }
        }
    }

@pytest.mark.asyncio
@respx.mock
async def test_crear_repo_nuevo_exito(base_config):
    provider = GitHubProvider(base_config)
    nombre_repo = "Math101-studentA"
    
    # 1. Mock GET -> 404 (no existe)
    respx.get(f"https://api.github.com/repos/test-org/{nombre_repo}").respond(status_code=404)
    
    # 2. Mock POST /generate -> 201 (creado exitosamente)
    respx.post(f"https://api.github.com/repos/test-org/test-template/generate").respond(
        status_code=201,
        json={"clone_url": f"https://github.com/test-org/{nombre_repo}.git"}
    )
    
    url = await provider.generar_repo_alumno(nombre_repo, "fake-oficial")
    assert url == f"https://github.com/test-org/{nombre_repo}.git"

@pytest.mark.asyncio
@respx.mock
async def test_repositorio_existente_reutilizacion(base_config):
    provider = GitHubProvider(base_config)
    nombre_repo = "Math101-studentB"
    
    # 1. Mock GET -> 200 (ya existe)
    respx.get(f"https://api.github.com/repos/test-org/{nombre_repo}").respond(
        status_code=200,
        json={"clone_url": f"https://github.com/test-org/{nombre_repo}.git"}
    )
    
    url = await provider.generar_repo_alumno(nombre_repo, "fake-oficial")
    assert url == f"https://github.com/test-org/{nombre_repo}.git"

@pytest.mark.asyncio
@respx.mock
async def test_generar_repo_fallo_controlado(base_config):
    provider = GitHubProvider(base_config)
    nombre_repo = "Math101-studentC"
    
    # 1. Mock GET -> 500 (falla la API de GitHub)
    respx.get(f"https://api.github.com/repos/test-org/{nombre_repo}").respond(status_code=500)
    
    with pytest.raises(GitHubProvisionError) as exc_info:
        await provider.generar_repo_alumno(nombre_repo, "fake-oficial")
    
    assert "HTTP 500" in str(exc_info.value)

@pytest.mark.asyncio
@patch('app.services.git.github_provider.os.getenv')
async def test_lectura_del_pat(mock_getenv, base_config):
    # Test reading PAT from env var
    mock_getenv.return_value = "env-pat-456"
    del base_config['git']['github']['pat']
    
    # Patch settings getattr as well to force fallback to getenv
    with patch('app.services.git.github_provider.getattr', return_value=None):
        provider = GitHubProvider(base_config)
        assert provider.pat == "env-pat-456"
        assert provider.headers["Authorization"] == "token env-pat-456"

@pytest.mark.asyncio
async def test_lectura_pat_falta_config(base_config):
    # Ensure it raises error if PAT is completely missing
    del base_config['git']['github']['pat']
    
    with patch('app.services.git.github_provider.os.getenv', return_value=None):
        with patch('app.services.git.github_provider.getattr', return_value=None):
            with pytest.raises(GitHubProvisionError) as exc_info:
                GitHubProvider(base_config)
            
            assert "GITHUB_PAT no está configurado" in str(exc_info.value)
