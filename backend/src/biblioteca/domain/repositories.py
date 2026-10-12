"""Interfaces (puertos) de los repositorios y de la unidad de trabajo.

El dominio define QUÉ necesita guardar y buscar; infrastructure/repositories implementa
CÓMO hacerlo con SQLAlchemy. La unidad de trabajo agrupa los cambios de un caso de uso
para confirmarlos juntos (ARCHITECTURE.md §3, Repository + Unit of Work).
"""

from typing import Protocol

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.entities.libro import Libro


class LibroRepository(Protocol):
    def existe(self, libro_id: int) -> bool: ...

    def existe_isbn(self, isbn: Isbn) -> bool: ...

    def existe_categoria(self, categoria_id: int) -> bool: ...

    def tiene_historial(self, libro_id: int) -> bool:
        """Verdadero si tiene ejemplares (aunque estén de baja) o reservas."""
        ...

    def agregar(self, libro: Libro) -> int: ...

    def eliminar(self, libro_id: int) -> None: ...


class UnidadDeTrabajo(Protocol):
    @property
    def libros(self) -> LibroRepository: ...

    def confirmar(self) -> None: ...
