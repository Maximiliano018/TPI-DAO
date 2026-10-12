from typing import Any

from fastapi import APIRouter, Response, status

from biblioteca.api.deps import Db, Uow
from biblioteca.api.schemas.catalogo import (
    CategoriaOut,
    CreadoOut,
    DisponibilidadLibroOut,
    EjemplarOut,
    LibroIn,
    LibroOut,
)
from biblioteca.application.reports.disponibilidad import disponibilidad
from biblioteca.application.services.catalogo import (
    DatosLibro,
    eliminar_libro,
    listar_categorias,
    listar_ejemplares,
    listar_libros,
    registrar_libro,
)
from biblioteca.domain.enums import EstadoEjemplar

router = APIRouter(tags=["catálogo"])


@router.get("/libros", response_model=list[LibroOut])
def get_libros(db: Db, buscar: str | None = None) -> list[dict[str, Any]]:
    """Busca por título, ISBN o autor."""
    return listar_libros(db, buscar)


@router.post("/libros", response_model=CreadoOut, status_code=status.HTTP_201_CREATED)
def post_libro(uow: Uow, datos: LibroIn) -> dict[str, int]:
    """Alta de libro. 409 si el ISBN ya existe; 422 si el ISBN no es válido."""
    return {"id": registrar_libro(uow, DatosLibro(**datos.model_dump()))}


@router.delete("/libros/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_libro(uow: Uow, libro_id: int) -> Response:
    """Solo para libros sin ejemplares ni reservas (409 si tienen historial)."""
    eliminar_libro(uow, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/categorias", response_model=list[CategoriaOut])
def get_categorias(db: Db) -> list[dict[str, Any]]:
    return listar_categorias(db)


@router.get("/ejemplares", response_model=list[EjemplarOut])
def get_ejemplares(
    db: Db,
    libro_id: int | None = None,
    sede_id: int | None = None,
    estado: EstadoEjemplar | None = None,
) -> list[dict[str, Any]]:
    return listar_ejemplares(db, libro_id, sede_id, estado)


@router.get("/disponibilidad", response_model=list[DisponibilidadLibroOut])
def get_disponibilidad(
    db: Db, buscar: str | None = None, sede_id: int | None = None
) -> list[dict[str, Any]]:
    """Ejemplares de cada libro en cada sede, por estado (reporte R5)."""
    return disponibilidad(db, buscar, sede_id)
