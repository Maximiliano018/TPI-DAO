"""Implementaciones de los puertos de seguridad: argon2 (pwdlib) y JWT (PyJWT)."""

from datetime import timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from biblioteca.application.security.puertos import TokenEmitido
from biblioteca.domain.clock import Reloj
from biblioteca.domain.errors import NoAutenticado


class HasherArgon2:
    def __init__(self) -> None:
        self._hash = PasswordHash((Argon2Hasher(),))

    def hashear(self, contrasena: str) -> str:
        return self._hash.hash(contrasena)

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return self._hash.verify(contrasena, hash_guardado)
        except UnknownHashError:
            return False


class TokensJwt:
    """Tokens HS256 con el id del usuario en `sub`.

    La expiración se controla con el Reloj del dominio (no con la hora del sistema),
    para poder probarla con fechas fijas.
    """

    ALGORITMO = "HS256"

    def __init__(self, secreto: str, duracion: timedelta, reloj: Reloj) -> None:
        self._secreto = secreto
        self._duracion = duracion
        self._reloj = reloj

    def emitir(self, usuario_id: int) -> TokenEmitido:
        ahora = self._reloj.ahora()
        expira = ahora + self._duracion
        token = jwt.encode(
            {"sub": str(usuario_id), "iat": ahora, "exp": expira},
            self._secreto,
            algorithm=self.ALGORITMO,
        )
        return TokenEmitido(token=token, expira_en=expira)

    def leer_usuario_id(self, token: str) -> int:
        try:
            datos = jwt.decode(
                token,
                self._secreto,
                algorithms=[self.ALGORITMO],
                options={"require": ["sub", "exp"], "verify_exp": False},
            )
            usuario_id = int(datos["sub"])
            expira = int(datos["exp"])
        except (jwt.InvalidTokenError, ValueError) as error:
            raise NoAutenticado("El token no es válido") from error
        if self._reloj.ahora().timestamp() >= expira:
            raise NoAutenticado("La sesión expiró; vuelva a iniciar sesión")
        return usuario_id
