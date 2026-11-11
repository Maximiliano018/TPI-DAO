"""Seguridad: hash de contraseñas con Argon2id.

Firma y verificación de JWT (HS256).
"""

from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.exceptions import TokenInvalido  # noqa: E402

_hasher = PasswordHasher()
# Hash de una contraseña inexistente: se verifica cuando el usuario no existe para que el
# tiempo de respuesta no revele si el usuario existe.
HASH_FICTICIO = _hasher.hash("contraseña-que-nadie-usa")


def hashear_clave(clave: str) -> str:
    """Devuelve el hash Argon2id de una contraseña."""
    return _hasher.hash(clave)


def verificar_clave(clave: str, hash_guardado: str) -> bool:
    """Indica si la contraseña coincide con el hash guardado."""
    try:
        return _hasher.verify(hash_guardado, clave)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


ALGORITMO_JWT = "HS256"


def crear_token(
    *, usuario_id: int, rol: str, sede_id: int | None, ahora: datetime, minutos: int, clave: str
) -> str:
    """Firma un JWT con ``sub``, ``rol``, ``sede_id``, ``iat`` y ``exp``."""
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "sede_id": sede_id,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(minutes=minutos)).timestamp()),
    }
    return jwt.encode(payload, clave, algorithm=ALGORITMO_JWT)


def decodificar_token(token: str, clave: str, ahora: datetime) -> dict[str, Any]:
    """Valida firma y vencimiento y devuelve el payload.

    El vencimiento se compara con ``ahora`` (reloj inyectado), no con la hora del sistema.

    Raises:
        TokenInvalido: Si el token está manipulado, vencido o mal formado.
    """
    try:
        payload = jwt.decode(
            token,
            clave,
            algorithms=[ALGORITMO_JWT],
            options={"require": ["sub", "exp"], "verify_exp": False, "verify_iat": False},
        )
    except jwt.PyJWTError as error:
        raise TokenInvalido("La sesión no es válida o venció. Ingrese de nuevo.") from error
    if payload["exp"] <= ahora.timestamp():
        raise TokenInvalido("La sesión no es válida o venció. Ingrese de nuevo.")
    return payload
