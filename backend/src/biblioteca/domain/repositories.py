"""Interfaces (puertos) de los repositorios y de la unidad de trabajo.

El dominio define QUÉ necesita guardar y buscar; infrastructure/repositories implementa
CÓMO hacerlo con SQLAlchemy. La unidad de trabajo agrupa los cambios de un caso de uso
para confirmarlos juntos (ARCHITECTURE.md §3, Repository + Unit of Work). Los
repositorios nunca confirman: eso lo hace `UnidadDeTrabajo.confirmar()`.
"""

from typing import Protocol

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.entities.libro import Libro
from biblioteca.domain.entities.sede import Sede
from biblioteca.domain.entities.usuario import Usuario


class LibroRepository(Protocol):
    def existe(self, libro_id: int) -> bool: ...

    def existe_isbn(self, isbn: Isbn) -> bool: ...

    def existe_categoria(self, categoria_id: int) -> bool: ...

    def tiene_historial(self, libro_id: int) -> bool:
        """Verdadero si tiene ejemplares (aunque estén de baja) o reservas."""
        ...

    def agregar(self, libro: Libro) -> int: ...

    def eliminar(self, libro_id: int) -> None: ...


class SedeRepository(Protocol):
    def agregar(self, sede: Sede) -> None: ...

    def obtener(self, sede_id: int) -> Sede | None: ...

    def existe_codigo(self, codigo: str) -> bool: ...

    def existe_nombre(self, nombre: str, excepto_id: int | None = None) -> bool: ...

    def tiene_actividad_abierta(self, sede_id: int) -> bool:
        """Préstamos, remitos o reservas en curso que involucran a la sede."""
        ...


class UsuarioRepository(Protocol):
    def agregar(self, usuario: Usuario) -> None: ...

    def obtener(self, usuario_id: int) -> Usuario | None: ...

    def obtener_por_username(self, username: str) -> Usuario | None: ...

    def existe_username(self, username: str) -> bool: ...


class UnidadDeTrabajo(Protocol):
    @property
    def libros(self) -> LibroRepository: ...

    @property
    def sedes(self) -> SedeRepository: ...

    @property
    def usuarios(self) -> UsuarioRepository: ...

    def confirmar(self) -> None:
        """Guarda los cambios del caso de uso. Las entidades nuevas reciben su id."""
        ...
