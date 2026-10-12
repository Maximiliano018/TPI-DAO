from sqlalchemy import ColumnElement, delete, exists, insert, select
from sqlalchemy.orm import Session

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.entities.libro import Libro, normalizar_nombre
from biblioteca.infrastructure.db.insercion import insertar
from biblioteca.infrastructure.db.tables import (
    autor,
    categoria,
    ejemplar,
    libro,
    libro_autor,
    reserva,
)


class SqlLibroRepository:
    """Implementación de `LibroRepository` con SQLAlchemy Core. No confirma: eso es del UoW."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _hay(self, condicion: ColumnElement[bool]) -> bool:
        return bool(self._session.execute(select(exists().where(condicion))).scalar())

    def existe(self, libro_id: int) -> bool:
        return self._hay(libro.c.id == libro_id)

    def existe_isbn(self, isbn: Isbn) -> bool:
        return self._hay(libro.c.isbn == isbn.valor)

    def existe_categoria(self, categoria_id: int) -> bool:
        return self._hay(categoria.c.id == categoria_id)

    def tiene_historial(self, libro_id: int) -> bool:
        return self._hay(ejemplar.c.libro_id == libro_id) or self._hay(
            reserva.c.libro_id == libro_id
        )

    def agregar(self, nuevo: Libro) -> int:
        conn = self._session.connection()
        libro_id = insertar(
            conn,
            libro,
            isbn=nuevo.isbn.valor,
            titulo=nuevo.titulo,
            editorial=nuevo.editorial,
            anio_publicacion=nuevo.anio_publicacion,
            categoria_id=nuevo.categoria_id,
        )
        for orden, nombre in enumerate(nuevo.autores, start=1):
            conn.execute(
                insert(libro_autor).values(
                    libro_id=libro_id, autor_id=self._autor_id(nombre), orden=orden
                )
            )
        nuevo.id = libro_id
        return libro_id

    def _autor_id(self, nombre: str) -> int:
        """Reutiliza el autor si ya existe con el mismo nombre normalizado."""
        normalizado = normalizar_nombre(nombre)
        existente = self._session.execute(
            select(autor.c.id).where(autor.c.nombre_normalizado == normalizado)
        ).scalar()
        if existente is not None:
            return int(existente)
        return insertar(
            self._session.connection(), autor, nombre=nombre, nombre_normalizado=normalizado
        )

    def eliminar(self, libro_id: int) -> None:
        # libro_autor se borra en cascada (FK con ON DELETE CASCADE).
        self._session.execute(delete(libro).where(libro.c.id == libro_id))
