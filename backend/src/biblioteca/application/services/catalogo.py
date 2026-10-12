"""Catálogo: casos de uso de libros y consultas de libros y ejemplares.

- Casos de uso (modifican datos): pasan por la entidad `Libro` y la unidad de trabajo.
- Consultas (solo lectura): van directo a las tablas.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.entities.libro import Libro
from biblioteca.domain.enums import EstadoEjemplar
from biblioteca.domain.errors import DuplicadoError, LibroConHistorial, NoEncontrado
from biblioteca.domain.repositories import UnidadDeTrabajo
from biblioteca.infrastructure.db.tables import autor, categoria, ejemplar, libro, libro_autor, sede

# ------------------------------------------------------------------------ Casos de uso


@dataclass(frozen=True)
class DatosLibro:
    isbn: str
    titulo: str
    autores: list[str]
    editorial: str | None = None
    anio_publicacion: int | None = None
    categoria_id: int | None = None


def registrar_libro(uow: UnidadDeTrabajo, datos: DatosLibro) -> int:
    """Alta de un libro en el catálogo de la red. El ISBN es la clave anti-duplicados."""
    nuevo = Libro(
        isbn=Isbn.desde_texto(datos.isbn),
        titulo=datos.titulo,
        autores=datos.autores,
        editorial=datos.editorial,
        anio_publicacion=datos.anio_publicacion,
        categoria_id=datos.categoria_id,
    )
    if uow.libros.existe_isbn(nuevo.isbn):
        raise DuplicadoError(f"Ya existe un libro con el ISBN {nuevo.isbn}")
    if nuevo.categoria_id is not None and not uow.libros.existe_categoria(nuevo.categoria_id):
        raise NoEncontrado(f"No existe la categoría {nuevo.categoria_id}")

    libro_id = uow.libros.agregar(nuevo)
    uow.confirmar()
    return libro_id


def eliminar_libro(uow: UnidadDeTrabajo, libro_id: int) -> None:
    """Borra un libro cargado por error. Si ya tiene historia, no se puede borrar."""
    if not uow.libros.existe(libro_id):
        raise NoEncontrado(f"No existe el libro {libro_id}")
    if uow.libros.tiene_historial(libro_id):
        raise LibroConHistorial(
            "No se puede eliminar: el libro tiene ejemplares o reservas registradas. "
            "Para sacarlo de circulación, dar de baja sus ejemplares."
        )
    uow.libros.eliminar(libro_id)
    uow.confirmar()


# ------------------------------------------------------------------------- Consultas


def listar_categorias(db: Session) -> list[dict[str, Any]]:
    consulta = select(categoria.c.id, categoria.c.nombre).order_by(categoria.c.nombre)
    return [dict(fila) for fila in db.execute(consulta).mappings()]


def listar_libros(db: Session, buscar: str | None) -> list[dict[str, Any]]:
    disponible = and_(
        ejemplar.c.estado == EstadoEjemplar.DISPONIBLE, ejemplar.c.prestable.is_(True)
    )
    consulta = (
        select(
            libro.c.id,
            libro.c.isbn,
            libro.c.titulo,
            libro.c.editorial,
            libro.c.anio_publicacion,
            categoria.c.nombre.label("categoria"),
            func.count(ejemplar.c.id).label("ejemplares"),
            func.coalesce(func.sum(case((disponible, 1), else_=0)), 0).label("disponibles"),
        )
        .select_from(
            libro.outerjoin(categoria, libro.c.categoria_id == categoria.c.id).outerjoin(
                ejemplar,
                and_(ejemplar.c.libro_id == libro.c.id, ejemplar.c.estado != EstadoEjemplar.BAJA),
            )
        )
        .group_by(libro.c.id, categoria.c.nombre)
        .order_by(libro.c.titulo)
    )
    if buscar:
        patron = f"%{buscar.strip()}%"
        de_autores = (
            select(libro_autor.c.libro_id)
            .join(autor, libro_autor.c.autor_id == autor.c.id)
            .where(autor.c.nombre.ilike(patron))
        )
        consulta = consulta.where(
            or_(libro.c.titulo.ilike(patron), libro.c.isbn.like(patron), libro.c.id.in_(de_autores))
        )
    libros = [dict(fila) for fila in db.execute(consulta).mappings()]

    autores: dict[int, list[str]] = {}
    consulta_autores = (
        select(libro_autor.c.libro_id, autor.c.nombre)
        .join(autor, libro_autor.c.autor_id == autor.c.id)
        .order_by(libro_autor.c.libro_id, libro_autor.c.orden)
    )
    for libro_id, nombre in db.execute(consulta_autores):
        autores.setdefault(libro_id, []).append(nombre)
    for item in libros:
        item["autores"] = autores.get(item["id"], [])
    return libros


def listar_ejemplares(
    db: Session,
    libro_id: int | None,
    sede_id: int | None,
    estado: EstadoEjemplar | None,
) -> list[dict[str, Any]]:
    consulta = (
        select(
            ejemplar.c.id,
            ejemplar.c.codigo_inventario,
            ejemplar.c.libro_id,
            libro.c.titulo,
            ejemplar.c.sede_id,
            sede.c.nombre.label("sede"),
            ejemplar.c.estado,
            ejemplar.c.condicion_fisica,
            ejemplar.c.prestable,
            ejemplar.c.fecha_alta,
            ejemplar.c.motivo_baja,
        )
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(sede, ejemplar.c.sede_id == sede.c.id)
        .order_by(libro.c.titulo, ejemplar.c.codigo_inventario)
    )
    if libro_id is not None:
        consulta = consulta.where(ejemplar.c.libro_id == libro_id)
    if sede_id is not None:
        consulta = consulta.where(ejemplar.c.sede_id == sede_id)
    if estado is not None:
        consulta = consulta.where(ejemplar.c.estado == estado)
    return [dict(fila) for fila in db.execute(consulta).mappings()]
