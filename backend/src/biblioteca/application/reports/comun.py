"""Piezas de SQL compartidas por los reportes."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Column, ColumnElement, case, func


def contar_si(condicion: ColumnElement[bool]) -> ColumnElement[int]:
    """Cantidad de filas del grupo que cumplen la condición (0 si ninguna)."""
    return func.coalesce(func.sum(case((condicion, 1), else_=0)), 0)


def filtro_periodo(
    columna: Column[datetime], desde: date | None, hasta: date | None
) -> list[ColumnElement[bool]]:
    """Condiciones para un período de días completos (ambos extremos incluidos)."""
    condiciones: list[ColumnElement[bool]] = []
    if desde is not None:
        condiciones.append(columna >= datetime.combine(desde, time(), tzinfo=UTC))
    if hasta is not None:
        condiciones.append(columna < datetime.combine(hasta + timedelta(1), time(), tzinfo=UTC))
    return condiciones
