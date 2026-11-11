"""Página de resultados."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pagina[T]:
    """Una página de ``items`` con el total de resultados."""

    items: list[T]
    total: int
    page: int
    size: int
