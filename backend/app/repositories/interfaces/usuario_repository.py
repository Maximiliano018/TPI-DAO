"""Puerto de acceso a usuarios."""

from dataclasses import dataclass
from typing import Protocol

from app.models.usuario import Rol, Usuario


@dataclass(frozen=True)
class FiltroUsuarios:
    """Filtros del listado de personal (el texto llega normalizado)."""

    rol: Rol | None = None
    sede_id: int | None = None
    activo: bool | None = None
    texto: str | None = None


class UsuarioRepository(Protocol):
    """Acceso a usuarios del sistema."""

    def obtener(self, usuario_id: int) -> Usuario | None:
        """Usuario por id, o ``None``. Es el camino de cada solicitud autenticada: sin auditoría."""
        ...

    def obtener_por_username(self, username: str) -> Usuario | None:
        """Usuario por nombre de usuario (en minúsculas), o ``None``."""
        ...

    def obtener_detalle(self, usuario_id: int) -> Usuario | None:
        """Usuario por id con los nombres de quien lo creó y lo modificó."""
        ...

    def obtener_para_modificar(self, usuario_id: int) -> Usuario | None:
        """Como ``obtener_detalle`` pero con la fila bloqueada (``FOR UPDATE``)."""
        ...

    def agregar(self, usuario: Usuario) -> None:
        """Persiste un usuario nuevo (asigna ``id``).

        Raises:
            DuplicadoError: El nombre de usuario ya existe (restricción única de la base).
        """
        ...

    def guardar(self, usuario: Usuario) -> None:
        """Persiste el nombre, la sede, el estado y la auditoría de un usuario cargado."""
        ...

    def listar(self, filtro: FiltroUsuarios, page: int, size: int) -> tuple[list[Usuario], int]:
        """Página de usuarios del personal (administradores y bibliotecarios) y total."""
        ...

    def bibliotecarios_activos_de_sede(
        self, sede_id: int, limite: int
    ) -> tuple[list[Usuario], int]:
        """Hasta ``limite`` bibliotecarios activos asignados a la sede, y el total."""
        ...
