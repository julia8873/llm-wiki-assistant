import pytest
from app.services.git import get_git_provider, GitProviderConfigError
from app.services.git.github_provider import GitHubProvider
from app.services.git.gitlab_provider import GitLabProvider
from app.services.git.self_hosted_provider import SelfHostedProvider
import os
import yaml
from unittest.mock import patch, mock_open

@pytest.fixture
def base_config():
    return {
        'git': {
            'proveedor_activo': 'github',
            'organizacion': 'test_org',
            'repo_plantilla': 'test_template',
            'github': {
                'api_base_url': 'https://api.github.com',
                'pat': 'test_pat'
            },
            'gitlab': {
                'api_base_url': 'https://gitlab.com/api/v4',
                'grupo_destino': 'test_group',
                'token_env_var': 'GITLAB_TOKEN'
            },
            'self_hosted': {
                'api_base_url': 'https://git.test.com/api/v4',
                'token_env_var': 'GIT_SELF_HOSTED_TOKEN'
            }
        }
    }

@patch('app.services.git.load_config')
def test_get_git_provider_github(mock_load_config, base_config):
    mock_load_config.return_value = base_config
    provider = get_git_provider()
    assert isinstance(provider, GitHubProvider)

@patch('app.services.git.load_config')
def test_get_git_provider_gitlab(mock_load_config, base_config):
    base_config['git']['proveedor_activo'] = 'gitlab'
    os.environ['GITLAB_TOKEN'] = 'test_token'
    mock_load_config.return_value = base_config
    provider = get_git_provider()
    assert isinstance(provider, GitLabProvider)

@patch('app.services.git.load_config')
def test_get_git_provider_self_hosted(mock_load_config, base_config):
    base_config['git']['proveedor_activo'] = 'self_hosted'
    mock_load_config.return_value = base_config
    provider = get_git_provider()
    assert isinstance(provider, SelfHostedProvider)

@patch('app.services.git.load_config')
def test_get_git_provider_invalid(mock_load_config, base_config):
    base_config['git']['proveedor_activo'] = 'invalid_provider'
    mock_load_config.return_value = base_config
    with pytest.raises(GitProviderConfigError):
        get_git_provider()
