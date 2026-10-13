from dataclasses import dataclass

from biblioteca.domain.enums import Rol


@dataclass(frozen=True, slots=True)
class UsuarioActual:
    """Quién ejecuta el caso de uso. Lo arma la API a partir del token."""

    id: int
    username: str
    nombre_completo: str
    rol: Rol
    sede_id: int | None

    @property
    def es_admin(self) -> bool:
        return self.rol == Rol.ADMIN
