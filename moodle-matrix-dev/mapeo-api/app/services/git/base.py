from abc import ABC, abstractmethod

class GitRateLimitError(Exception):
    """!
    @brief Excepción base para errores de Rate Limit en proveedores Git.
    """
    def __init__(self, message: str, retry_after_seconds: int):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

class GitHubRateLimitError(GitRateLimitError):
    """!
    @brief Error específico de Rate Limit para GitHub.
    """
    pass

class GitLabRateLimitError(GitRateLimitError):
    """!
    @brief Error específico de Rate Limit para GitLab.
    """
    pass
class GitProviderClient(ABC):
    """!
    @brief Interfaz base para los clientes de proveedores Git.
    """
    
    @abstractmethod
    async def crear_repo_oficial(self, nombre_asignatura: str, template_id: str) -> str:
        """!
        @brief Crea el repositorio oficial de la asignatura a partir del template OKF.
        @param nombre_asignatura Nombre de la asignatura.
        @param template_id Identificador o nombre del repositorio plantilla.
        @return URL de clonación del repositorio creado.
        """
        pass

    @abstractmethod
    async def marcar_como_template(self, repo_url: str) -> None:
        """!
        @brief Marca el repositorio dado como plantilla.
        @param repo_url URL del repositorio a marcar.
        """
        pass

    @abstractmethod
    async def generar_repo_alumno(self, nombre_repo: str, repo_oficial_url: str) -> str:
        """!
        @brief Genera un repositorio independiente para un alumno basado en el repo oficial.
        @details Garantiza que sea una copia sin historial compartido ni relación de fork
        visible en la API del proveedor.
        @param nombre_repo Nombre del nuevo repositorio.
        @param repo_oficial_url URL o identificador del repositorio oficial a copiar.
        @return URL de clonación del repositorio creado.
        """
        pass

    @abstractmethod
    async def existe_repo(self, repo_url: str) -> bool:
        """!
        @brief Verifica si un repositorio ya existe.
        @param repo_url URL o identificador del repositorio.
        @return True si existe, False en caso contrario.
        """
        pass
