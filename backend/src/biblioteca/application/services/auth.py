"""Autenticación: login y resolución del usuario a partir del token (ARCHITECTURE.md §6.2)."""

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.puertos import HasherContrasenas, ServicioTokens, TokenEmitido
from biblioteca.domain.errors import CredencialesInvalidas, NoAutenticado
from biblioteca.domain.repositories import UnidadDeTrabajo


def iniciar_sesion(
    uow: UnidadDeTrabajo,
    hasher: HasherContrasenas,
    tokens: ServicioTokens,
    username: str,
    contrasena: str,
) -> TokenEmitido:
    usuario = uow.usuarios.obtener_por_username(username.strip().lower())
    if usuario is None:
        # Se verifica igual contra un hash: el tiempo de respuesta no revela qué usuarios existen.
        hasher.verificar(contrasena, _hash_ficticio(hasher))
        raise CredencialesInvalidas("Usuario o contraseña incorrectos")
    if not hasher.verificar(contrasena, usuario.password_hash) or not usuario.activo:
        raise CredencialesInvalidas("Usuario o contraseña incorrectos")
    assert usuario.id is not None
    return tokens.emitir(usuario.id)


def resolver_usuario(uow: UnidadDeTrabajo, tokens: ServicioTokens, token: str) -> UsuarioActual:
    """Valida el token y recarga el usuario: si lo desactivaron, el token deja de servir."""
    usuario = uow.usuarios.obtener(tokens.leer_usuario_id(token))
    if usuario is None or usuario.id is None or not usuario.activo:
        raise NoAutenticado("La sesión no es válida; vuelva a iniciar sesión")
    return UsuarioActual(
        id=usuario.id,
        username=usuario.username,
        nombre_completo=usuario.nombre_completo,
        rol=usuario.rol,
        sede_id=usuario.sede_id,
    )


_hashes_ficticios: dict[type, str] = {}


def _hash_ficticio(hasher: HasherContrasenas) -> str:
    """Hash de una contraseña que nadie conoce, calculado una vez por tipo de hasher."""
    tipo = type(hasher)
    if tipo not in _hashes_ficticios:
        _hashes_ficticios[tipo] = hasher.hashear("contraseña-ficticia-no-usar")
    return _hashes_ficticios[tipo]
