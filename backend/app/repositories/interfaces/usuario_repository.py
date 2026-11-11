"""Puerto de acceso a usuarios."""

from typing import Protocol

from app.models.usuario import Usuario


class UsuarioRepository(Protocol):
    """Acceso a usuarios del sistema."""

    def obtener(self, usuario_id: int) -> Usuario | None:
        """Usuario por id, o ``None``."""
        ...

    def obtener_por_username(self, username: str) -> Usuario | None:
        """Usuario por nombre de usuario (en minúsculas), o ``None``."""
        ...
