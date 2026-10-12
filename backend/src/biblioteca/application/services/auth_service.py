from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.puertos import HasherContrasenas, ServicioTokens, TokenEmitido
from biblioteca.application.unit_of_work import UnitOfWork
from biblioteca.domain.errors import CredencialesInvalidas, NoAutenticado


class AuthService:
    """Login y resolución del usuario a partir del token (ARCHITECTURE.md §6.2)."""

    # Hash de una contraseña que nadie conoce. Se verifica contra él cuando el usuario no
    # existe, para que el tiempo de respuesta no revele qué nombres de usuario son válidos.
    _hash_ficticio: str | None = None

    def __init__(self, uow: UnitOfWork, hasher: HasherContrasenas, tokens: ServicioTokens) -> None:
        self.uow = uow
        self.hasher = hasher
        self.tokens = tokens

    def login(self, username: str, contrasena: str) -> TokenEmitido:
        with self.uow:
            usuario = self.uow.usuarios.obtener_por_username(username.strip().lower())
        if usuario is None:
            self.hasher.verificar(contrasena, self._obtener_hash_ficticio())
            raise CredencialesInvalidas("Usuario o contraseña incorrectos")
        if not self.hasher.verificar(contrasena, usuario.password_hash) or not usuario.activo:
            raise CredencialesInvalidas("Usuario o contraseña incorrectos")
        assert usuario.id is not None
        return self.tokens.emitir(usuario.id)

    def usuario_actual(self, token: str) -> UsuarioActual:
        """Valida el token y recarga el usuario: si lo desactivaron, el token deja de servir."""
        usuario_id = self.tokens.leer_usuario_id(token)
        with self.uow:
            usuario = self.uow.usuarios.obtener(usuario_id)
        if usuario is None or not usuario.activo or usuario.id is None:
            raise NoAutenticado("La sesión no es válida; vuelva a iniciar sesión")
        return UsuarioActual(
            id=usuario.id,
            username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            rol=usuario.rol,
            sede_id=usuario.sede_id,
        )

    def _obtener_hash_ficticio(self) -> str:
        if AuthService._hash_ficticio is None:
            AuthService._hash_ficticio = self.hasher.hashear("contraseña-ficticia-no-usar")
        return AuthService._hash_ficticio
