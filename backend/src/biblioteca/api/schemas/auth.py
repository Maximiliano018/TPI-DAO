from datetime import datetime

from pydantic import BaseModel

from biblioteca.domain.enums import Rol


class TokenSalida(BaseModel):
    """Formato OAuth2 (lo usa también el botón "Authorize" de Swagger)."""

    access_token: str
    token_type: str = "bearer"
    expira_en: datetime


class UsuarioActualSalida(BaseModel):
    id: int
    username: str
    nombre_completo: str
    rol: Rol
    sede_id: int | None
