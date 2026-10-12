"""Interfaces (puertos) de los repositorios.

El dominio define QUÉ necesita guardar y buscar; infrastructure/repositories
implementa CÓMO hacerlo con SQLAlchemy. Los repositorios no confirman cambios:
eso lo hace la Unidad de Trabajo (application/unit_of_work.py).
"""

from typing import Protocol

from biblioteca.domain.entities.sede import Sede
from biblioteca.domain.entities.usuario import Usuario


class SedeRepository(Protocol):
    def agregar(self, sede: Sede) -> None: ...

    def obtener(self, sede_id: int) -> Sede | None: ...

    def existe_codigo(self, codigo: str) -> bool: ...

    def existe_nombre(self, nombre: str, excepto_id: int | None = None) -> bool: ...

    def listar(self, *, solo_activas: bool, limite: int, desde: int) -> list[Sede]: ...

    def contar(self, *, solo_activas: bool) -> int: ...

    def tiene_actividad_abierta(self, sede_id: int) -> bool:
        """Préstamos, remitos o reservas en curso que involucran a la sede."""
        ...


class UsuarioRepository(Protocol):
    def agregar(self, usuario: Usuario) -> None: ...

    def obtener(self, usuario_id: int) -> Usuario | None: ...

    def obtener_por_username(self, username: str) -> Usuario | None: ...

    def existe_username(self, username: str) -> bool: ...
