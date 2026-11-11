"""Usuario del sistema, roles y permisos.

Los roles son tres y fijos (los define el enunciado). Los permisos se resuelven en el servidor
a partir del rol: ``ROL_PERMISOS`` es la única fuente de verdad.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.exceptions import PermisoDenegado


class Rol(StrEnum):
    """Rol de un usuario."""

    ADMIN = "ADMIN"
    BIBLIOTECARIO = "BIBLIOTECARIO"
    SOCIO = "SOCIO"


class Permiso(StrEnum):
    """Capacidad concreta que un endpoint o caso de uso puede exigir."""

    SEDE_LEER_PUBLICO = "SEDE_LEER_PUBLICO"
    SEDE_LEER_BASICO = "SEDE_LEER_BASICO"
    SEDE_LEER_COMPLETO = "SEDE_LEER_COMPLETO"
    SEDE_ADMINISTRAR = "SEDE_ADMINISTRAR"
    SEDE_VER_HISTORIAL = "SEDE_VER_HISTORIAL"
    USUARIO_ADMINISTRAR = "USUARIO_ADMINISTRAR"


ROL_PERMISOS: dict[Rol, frozenset[Permiso]] = {
    Rol.ADMIN: frozenset(
        {
            Permiso.SEDE_LEER_PUBLICO,
            Permiso.SEDE_LEER_BASICO,
            Permiso.SEDE_LEER_COMPLETO,
            Permiso.SEDE_ADMINISTRAR,
            Permiso.SEDE_VER_HISTORIAL,
            Permiso.USUARIO_ADMINISTRAR,
        }
    ),
    Rol.BIBLIOTECARIO: frozenset({Permiso.SEDE_LEER_PUBLICO, Permiso.SEDE_LEER_BASICO}),
    Rol.SOCIO: frozenset({Permiso.SEDE_LEER_PUBLICO}),
}


@dataclass(frozen=True)
class SedeRef:
    """Referencia liviana a una sede (la usa el usuario para mostrar su sede)."""

    id: int
    codigo: str
    nombre: str


@dataclass
class Usuario:
    """Usuario autenticable. ``sede`` solo corresponde al bibliotecario."""

    id: int | None
    username: str
    nombre: str
    rol: Rol
    activo: bool = True
    sede: SedeRef | None = None
    socio_id: int | None = None
    password_hash: str = ""

    @property
    def sede_id(self) -> int | None:
        """Id de la sede asignada (``None`` para administradores y socios)."""
        return self.sede.id if self.sede else None

    @property
    def permisos(self) -> frozenset[Permiso]:
        """Permisos que le da su rol."""
        return ROL_PERMISOS[self.rol]

    def puede(self, permiso: Permiso) -> bool:
        """Indica si el usuario tiene el permiso."""
        return permiso in self.permisos

    def exigir(self, permiso: Permiso) -> None:
        """Lanza ``PermisoDenegado`` si el usuario no tiene el permiso."""
        if not self.puede(permiso):
            raise PermisoDenegado("No tiene permiso para realizar esta operación.")

    def opera_en(self, sede_id: int) -> bool:
        """Un bibliotecario opera solo en su sede; el administrador no opera por sede."""
        return self.rol == Rol.BIBLIOTECARIO and self.sede_id == sede_id
