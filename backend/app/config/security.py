"""Seguridad: hash de contraseñas con Argon2id.

La firma y verificación de JWT se suma en el módulo de autenticación.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

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
