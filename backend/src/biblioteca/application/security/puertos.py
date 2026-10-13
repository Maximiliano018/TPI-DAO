"""Puertos de seguridad: la aplicación define qué necesita y la infraestructura lo provee."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class HasherContrasenas(Protocol):
    def hashear(self, contrasena: str) -> str: ...

    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class TokenEmitido:
    token: str
    expira_en: datetime


class ServicioTokens(Protocol):
    def emitir(self, usuario_id: int) -> TokenEmitido: ...

    def leer_usuario_id(self, token: str) -> int:
        """Devuelve el id del usuario del token o lanza `NoAutenticado`."""
        ...
