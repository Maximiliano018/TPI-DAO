from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

from biblioteca.application.paginacion import LIMITE_MAXIMO, LIMITE_POR_DEFECTO


class PaginaSalida[T](BaseModel):
    items: list[T]
    total: int
    limite: int
    desde: int


class ParametrosPagina(BaseModel):
    limite: int
    desde: int


def paginacion(
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = LIMITE_POR_DEFECTO,
    desde: Annotated[int, Query(ge=0)] = 0,
) -> ParametrosPagina:
    """Dependencia para listados: `?limite=50&desde=0`."""
    return ParametrosPagina(limite=limite, desde=desde)


class ErrorSalida(BaseModel):
    codigo: str
    mensaje: str
    detalle: object | None = None
