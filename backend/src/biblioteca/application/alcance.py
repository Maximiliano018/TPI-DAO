"""Alcance de los datos según la sede del usuario (ARCHITECTURE.md §6.1).

El ADMIN ve toda la red; el resto del personal ve lo que involucra a su sede. Las
consultas reciben `sede_id`: `None` significa "toda la red".
"""

from typing import Any

from sqlalchemy import ColumnElement, or_

from biblioteca.application.security.actor import UsuarioActual


def sede_de_alcance(actor: UsuarioActual) -> int | None:
    return None if actor.es_admin else actor.sede_id


def involucra_sede(sede_id: int | None, *columnas: Any) -> list[ColumnElement[bool]]:
    """Condición para filas donde alguna de las columnas es la sede (origen o destino, por
    ejemplo). Sin sede no filtra: se usa como `consulta.where(*involucra_sede(...))`."""
    if sede_id is None:
        return []
    return [or_(*(columna == sede_id for columna in columnas))]
