from .base import GitProviderClient

class SelfHostedProvider(GitProviderClient):
    """!
    @brief Proveedor Git autoalojado (Gitea/Forgejo o GitLab CE/EE).
    @details Pendiente de definir la tecnología exacta en config.yaml por la UGR.
    Se implementará una vez se defina el software exacto (ej. Gitea usa /generate, GitLab usa fork).
    """
    def __init__(self, config: dict):
        self.config = config
        
    async def crear_repo_oficial(self, nombre_asignatura: str, template_id: str = None) -> str:
        raise NotImplementedError("SelfHostedProvider pendiente de definición tecnológica (OSL).")

    async def marcar_como_template(self, repo_url: str) -> None:
        raise NotImplementedError("SelfHostedProvider pendiente de definición tecnológica (OSL).")

    async def generar_repo_alumno(self, nombre_repo: str, repo_oficial_url: str) -> str:
        raise NotImplementedError("SelfHostedProvider pendiente de definición tecnológica (OSL).")

    async def existe_repo(self, repo_url: str) -> bool:
        raise NotImplementedError("SelfHostedProvider pendiente de definición tecnológica (OSL).")
        
    async def crear_commit_archivo(self, repo_url: str, path: str, content: str, message: str) -> str:
        raise NotImplementedError("SelfHostedProvider pendiente de definición tecnológica (OSL).")
