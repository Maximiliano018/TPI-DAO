"""Usuarios del personal. Por ahora solo el alta del ADMIN inicial; el ABM completo
(alta por el ADMIN, desactivar, resetear contraseña) llega en la fase 2."""

from biblioteca.application.security.puertos import HasherContrasenas
from biblioteca.domain.entities.usuario import Usuario, validar_contrasena
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import DuplicadoError
from biblioteca.domain.repositories import UnidadDeTrabajo


def registrar_admin(
    uow: UnidadDeTrabajo,
    hasher: HasherContrasenas,
    username: str,
    nombre_completo: str,
    contrasena: str,
) -> Usuario:
    """Alta de un ADMIN sin actor: solo se usa desde la CLI del servidor."""
    validar_contrasena(contrasena)
    nuevo = Usuario(username, nombre_completo, hasher.hashear(contrasena), Rol.ADMIN, None)
    if uow.usuarios.existe_username(nuevo.username):
        raise DuplicadoError(f"Ya existe el usuario {nuevo.username}")
    uow.usuarios.agregar(nuevo)
    uow.confirmar()
    return nuevo
