"""Préstamos: consultas (solo lectura)."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.domain.enums import ESTADOS_PRESTAMO_ABIERTOS, EstadoPrestamo
from biblioteca.infrastructure.db.tables import ejemplar, libro, prestamo, sede, socio

origen = sede.alias("origen")
destino = sede.alias("destino")


def listar_prestamos(
    db: Session,
    hoy: date,
    estado: EstadoPrestamo | None,
    solo_abiertos: bool,
    limit: int,
    offset: int,
    *,
    sede_id: int | None,
) -> list[dict[str, Any]]:
    """Con `sede_id`, solo los préstamos donde la sede es origen o destino."""
    consulta = (
        select(
            prestamo.c.id,
            prestamo.c.estado,
            prestamo.c.fecha_solicitud,
            prestamo.c.fecha_limite_retiro,
            prestamo.c.fecha_inicio,
            prestamo.c.fecha_vencimiento,
            prestamo.c.fecha_cierre,
            prestamo.c.motivo_cancelacion,
            socio.c.id.label("socio_id"),
            (socio.c.apellido + ", " + socio.c.nombre).label("socio"),
            socio.c.numero_socio,
            ejemplar.c.codigo_inventario,
            libro.c.titulo,
            origen.c.id.label("sede_origen_id"),
            origen.c.nombre.label("sede_origen"),
            destino.c.id.label("sede_destino_id"),
            destino.c.nombre.label("sede_destino"),
        )
        .join(socio, prestamo.c.socio_id == socio.c.id)
        .join(ejemplar, prestamo.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(origen, prestamo.c.sede_origen_id == origen.c.id)
        .join(destino, prestamo.c.sede_destino_id == destino.c.id)
        .where(*involucra_sede(sede_id, prestamo.c.sede_origen_id, prestamo.c.sede_destino_id))
        .order_by(prestamo.c.fecha_solicitud.desc())
        .limit(limit)
        .offset(offset)
    )
    if estado is not None:
        consulta = consulta.where(prestamo.c.estado == estado)
    if solo_abiertos:
        consulta = consulta.where(prestamo.c.estado.in_(ESTADOS_PRESTAMO_ABIERTOS))

    resultado = []
    for fila in db.execute(consulta).mappings():
        p = dict(fila)
        # Condiciones derivadas, no guardadas (ARCHITECTURE.md §4.4).
        p["tipo"] = "LOCAL" if p["sede_origen_id"] == p["sede_destino_id"] else "INTERSEDES"
        vencido = p["estado"] == EstadoPrestamo.ACTIVO and hoy > p["fecha_vencimiento"]
        p["vencido"] = vencido
        p["dias_atraso"] = (hoy - p["fecha_vencimiento"]).days if vencido else 0
        p["retiro_vencido"] = (
            p["estado"] == EstadoPrestamo.LISTO_PARA_RETIRO and hoy > p["fecha_limite_retiro"]
        )
        resultado.append(p)
    return resultado
