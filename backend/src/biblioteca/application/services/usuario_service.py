from biblioteca.application.security.puertos import HasherContrasenas
from biblioteca.application.unit_of_work import UnitOfWork
from biblioteca.domain.entities.usuario import Usuario, validar_contrasena
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import DuplicadoError


class UsuarioService:
    """Gestión de usuarios. Por ahora solo el alta del ADMIN inicial; el ABM completo
    (alta por el ADMIN, desactivar, resetear contraseña) llega en la fase 2."""

    def __init__(self, uow: UnitOfWork, hasher: HasherContrasenas) -> None:
        self.uow = uow
        self.hasher = hasher

    def registrar_admin(self, username: str, nombre_completo: str, contrasena: str) -> Usuario:
        """Alta de un ADMIN sin actor: solo se usa desde la CLI del servidor."""
        validar_contrasena(contrasena)
        usuario = Usuario(
            username, nombre_completo, self.hasher.hashear(contrasena), Rol.ADMIN, sede_id=None
        )
        with self.uow:
            if self.uow.usuarios.existe_username(usuario.username):
                raise DuplicadoError(f"Ya existe el usuario {usuario.username}")
            self.uow.usuarios.agregar(usuario)
            self.uow.commit()
            return usuario
