from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno o del archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BIBLIOTECA_")

    database_url: str = "sqlite:///./biblioteca.db"
    api_prefix: str = "/api/v1"


settings = Settings()
