from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno (prefijo BIBLIOTECA_) o del archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BIBLIOTECA_")

    database_url: str = "sqlite:///./biblioteca.db"
    api_prefix: str = "/api/v1"

    # Zona horaria de la red: define qué día es "hoy" para vencimientos y plazos.
    zona_horaria: str = "America/Argentina/Buenos_Aires"

    # Secreto para firmar los JWT. Si no se define, se genera uno al iniciar la API y las
    # sesiones se pierden al reiniciarla (cómodo en desarrollo, inaceptable en producción).
    jwt_secreto: str | None = None
    # Duración de la sesión: una jornada de trabajo.
    jwt_expira_minutos: int = 480


settings = Settings()
