"""Reservas: consultas (solo lectura)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.domain.enums import ESTADOS_RESERVA_ABIERTOS, EstadoReserva
from biblioteca.infrastructure.db.tables import ejemplar, libro, reserva, sede, socio


def listar_reservas(
    db: Session, estado: EstadoReserva | None, solo_abiertas: bool, *, sede_id: int | None
) -> list[dict[str, Any]]:
    """Con `sede_id`, solo las reservas cuya sede de retiro es esa."""
    consulta = (
        select(
            reserva.c.id,
            reserva.c.estado,
            reserva.c.fecha_solicitud,
            reserva.c.fecha_asignacion,
            reserva.c.fecha_limite,
            reserva.c.fecha_cierre,
            reserva.c.libro_id,
            reserva.c.sede_id,
            (socio.c.apellido + ", " + socio.c.nombre).label("socio"),
            libro.c.titulo,
            sede.c.nombre.label("sede"),
            ejemplar.c.codigo_inventario.label("ejemplar_asignado"),
        )
        .join(socio, reserva.c.socio_id == socio.c.id)
        .join(libro, reserva.c.libro_id == libro.c.id)
        .join(sede, reserva.c.sede_id == sede.c.id)
        .outerjoin(ejemplar, reserva.c.ejemplar_asignado_id == ejemplar.c.id)
        .where(*involucra_sede(sede_id, reserva.c.sede_id))
        .order_by(reserva.c.fecha_solicitud)
    )
    if estado is not None:
        consulta = consulta.where(reserva.c.estado == estado)
    if solo_abiertas:
        consulta = consulta.where(reserva.c.estado.in_(ESTADOS_RESERVA_ABIERTOS))

    reservas = [dict(fila) for fila in db.execute(consulta).mappings()]

    # Posición en la cola FIFO de cada libro y sede (solo las pendientes esperan turno).
    ultima_posicion: dict[tuple[int, int], int] = {}
    for r in reservas:
        if r["estado"] == EstadoReserva.PENDIENTE:
            clave = (r["libro_id"], r["sede_id"])
            ultima_posicion[clave] = ultima_posicion.get(clave, 0) + 1
            r["posicion_cola"] = ultima_posicion[clave]
        else:
            r["posicion_cola"] = None
    return reservas
