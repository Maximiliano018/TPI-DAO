"""Configuración de la aplicación leída de variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_REPO = Path(__file__).resolve().parents[3]
CLAVE_DE_EJEMPLO = "cambiar_esta_clave_larga_de_al_menos_32_caracteres"
LARGO_MINIMO_CLAVE = 32


class Settings(BaseSettings):
    """Variables de entorno del backend (ver ``.env.example``)."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_REPO / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://tpi_dao:tpi_dao@localhost:5432/tpi_dao"
    database_url_test: str | None = None
    secret_key: str = CLAVE_DE_EJEMPLO
    access_token_minutes: int = Field(default=60, ge=1)
    cors_origins: str = "http://localhost:5173"
    tz_negocio: str = "America/Argentina/Cordoba"
    entorno: str = "desarrollo"
    seed_password: str | None = None

    @property
    def origenes_cors(self) -> list[str]:
        """Orígenes permitidos para CORS, separados por coma en la variable."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validar_clave_secreta(self) -> None:
        """Rechaza una clave de firma insegura (la de ejemplo o demasiado corta).

        Raises:
            RuntimeError: Si ``SECRET_KEY`` no es segura.
        """
        if self.secret_key == CLAVE_DE_EJEMPLO or len(self.secret_key) < LARGO_MINIMO_CLAVE:
            raise RuntimeError(
                f"SECRET_KEY debe definirse con al menos {LARGO_MINIMO_CLAVE} caracteres "
                "y no puede ser el valor de ejemplo."
            )


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración (se lee una sola vez)."""
    return Settings()
