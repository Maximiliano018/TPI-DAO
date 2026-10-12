import re

from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import DatoInvalido, TransicionInvalida
from biblioteca.domain.valores import texto_requerido

LARGO_MINIMO_CONTRASENA = 8


class Usuario:
    """Persona del personal que opera el sistema.

    Invariante: el ADMIN no tiene sede; el resto de los roles pertenece a una sola sede.
    La contraseña nunca se guarda en claro: el dominio solo conoce su hash.
    """

    id: int | None

    def __init__(
        self,
        username: str,
        nombre_completo: str,
        password_hash: str,
        rol: Rol,
        sede_id: int | None,
    ) -> None:
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,50}", username):
            raise DatoInvalido(
                "El usuario debe tener entre 3 y 50 caracteres: letras, números, '.', '_' o '-'"
            )
        self.id = None
        self.username = username
        self.nombre_completo = texto_requerido(nombre_completo, "nombre completo", 150)
        self.password_hash = password_hash
        self.activo = True
        self.asignar_rol(rol, sede_id)

    def asignar_rol(self, rol: Rol, sede_id: int | None) -> None:
        if rol == Rol.ADMIN and sede_id is not None:
            raise DatoInvalido("El ADMIN opera sobre toda la red y no tiene sede asignada")
        if rol != Rol.ADMIN and sede_id is None:
            raise DatoInvalido(f"Un usuario {rol} debe tener una sede asignada")
        self.rol = rol
        self.sede_id = sede_id

    def cambiar_password_hash(self, nuevo_hash: str) -> None:
        self.password_hash = nuevo_hash

    def desactivar(self) -> None:
        if not self.activo:
            raise TransicionInvalida(f"El usuario {self.username} ya está desactivado")
        self.activo = False

    def activar(self) -> None:
        if self.activo:
            raise TransicionInvalida(f"El usuario {self.username} ya está activo")
        self.activo = True


def validar_contrasena(contrasena: str) -> None:
    """Reglas mínimas de contraseña (ARCHITECTURE.md §6.2)."""
    if len(contrasena) < LARGO_MINIMO_CONTRASENA:
        raise DatoInvalido(
            f"La contraseña debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres"
        )
