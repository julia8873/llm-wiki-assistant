import os
import yaml
from .base import GitProviderClient

class GitProviderConfigError(Exception):
    pass

def load_config():
    """!
    @brief Carga la configuración desde config.yaml.
    @details Busca la configuración en la ruta definida por la variable de entorno
    CONFIG_PATH y si no existe usa un fallback local.
    
    @return dict|None Retorna la configuración como diccionario o None si falla.
    """
    config_path = os.getenv("CONFIG_PATH", "/config/config.yaml")
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback para tests locales
        local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../config/config.yaml"))
        if os.path.exists(local_path):
            with open(local_path, 'r') as f:
                return yaml.safe_load(f)
        return None

def get_git_provider() -> GitProviderClient:
    """!
    @brief Factoría para obtener el cliente del proveedor Git configurado.
    @return Instancia de GitProviderClient concreta.
    """
    config = load_config()
    if not config or 'git' not in config:
        raise GitProviderConfigError("Configuración 'git' no encontrada en config.yaml")

    proveedor = config['git'].get('proveedor_activo', 'github')

    if proveedor == 'github':
        from .github_provider import GitHubProvider
        return GitHubProvider(config)
    elif proveedor == 'gitlab':
        from .gitlab_provider import GitLabProvider
        return GitLabProvider(config)
    elif proveedor == 'self_hosted':
        from .self_hosted_provider import SelfHostedProvider
        return SelfHostedProvider(config)
    else:
        raise GitProviderConfigError(f"Proveedor Git no soportado: {proveedor}")
