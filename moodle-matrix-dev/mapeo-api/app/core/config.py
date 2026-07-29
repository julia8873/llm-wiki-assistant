from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración central del microservicio mapeo-api."""

    GITHUB_PAT: str | None = None

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
