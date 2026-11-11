"""Casos de uso de autenticación."""

from dataclasses import dataclass

from app.config import Settings
from app.config.security import (
    HASH_FICTICIO,
    crear_token,
    decodificar_token,
    verificar_clave,
)
from app.exceptions import CredencialesInvalidas, TokenInvalido
from app.models.usuario import Usuario
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj


@dataclass(frozen=True)
class ResultadoLogin:
    """Token emitido y usuario autenticado."""

    token: str
    expira_en_segundos: int
    usuario: Usuario


class AuthService:
    """Inicio de sesión y verificación de tokens."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj, settings: Settings) -> None:
        self._uow = uow
        self._reloj = reloj
        self._settings = settings

    def login(self, username: str, password: str) -> ResultadoLogin:
        """Valida las credenciales y emite un token.

        El mensaje de error es siempre el mismo (no revela cuál dato falló) y se verifica un
        hash ficticio cuando el usuario no existe, para igualar los tiempos de respuesta.

        Raises:
            CredencialesInvalidas: Usuario inexistente, dado de baja o contraseña incorrecta.
        """
        usuario = self._uow.usuarios.obtener_por_username(username.strip().lower())
        clave_ok = verificar_clave(password, usuario.password_hash if usuario else HASH_FICTICIO)
        if usuario is None or not clave_ok or not usuario.activo or usuario.id is None:
            raise CredencialesInvalidas("Usuario o contraseña incorrectos.")
        minutos = self._settings.access_token_minutes
        token = crear_token(
            usuario_id=usuario.id,
            rol=usuario.rol.value,
            sede_id=usuario.sede_id,
            ahora=self._reloj.ahora(),
            minutos=minutos,
            clave=self._settings.secret_key,
        )
        return ResultadoLogin(token=token, expira_en_segundos=minutos * 60, usuario=usuario)

    def autenticar(self, token: str) -> Usuario:
        """Devuelve el usuario del token, **recargado de la base** en cada solicitud.

        Así un usuario dado de baja, reasignado o con otro rol queda reflejado de inmediato.

        Raises:
            TokenInvalido: Token inválido o vencido, o usuario inexistente o dado de baja.
        """
        payload = decodificar_token(token, self._settings.secret_key, self._reloj.ahora())
        try:
            usuario_id = int(payload["sub"])
        except (KeyError, ValueError) as error:
            raise TokenInvalido("La sesión no es válida.") from error
        usuario = self._uow.usuarios.obtener(usuario_id)
        if usuario is None or not usuario.activo:
            raise TokenInvalido("La sesión no es válida o venció. Ingrese de nuevo.")
        return usuario
