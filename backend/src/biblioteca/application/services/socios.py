"""Socios: consultas (solo lectura)."""

from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from biblioteca.domain.enums import ESTADOS_PRESTAMO_ABIERTOS, EstadoMulta
from biblioteca.infrastructure.db.tables import multa, prestamo, socio


def listar_socios(db: Session, buscar: str | None, limit: int, offset: int) -> list[dict[str, Any]]:
    prestamos_abiertos = (
        select(func.count())
        .where(
            prestamo.c.socio_id == socio.c.id,
            prestamo.c.estado.in_(ESTADOS_PRESTAMO_ABIERTOS),
        )
        .scalar_subquery()
    )
    multas_pendientes = (
        select(func.coalesce(func.sum(multa.c.monto), 0))
        .select_from(multa.join(prestamo, multa.c.prestamo_id == prestamo.c.id))
        .where(prestamo.c.socio_id == socio.c.id, multa.c.estado == EstadoMulta.PENDIENTE)
        .scalar_subquery()
    )
    consulta = (
        select(
            socio.c.id,
            socio.c.numero_socio,
            socio.c.dni,
            socio.c.nombre,
            socio.c.apellido,
            socio.c.email,
            socio.c.telefono,
            socio.c.habilitado,
            socio.c.motivo_inhabilitacion,
            socio.c.activo,
            prestamos_abiertos.label("prestamos_abiertos"),
            multas_pendientes.label("multas_pendientes"),
        )
        .order_by(socio.c.apellido, socio.c.nombre)
        .limit(limit)
        .offset(offset)
    )
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(
                socio.c.dni.like(patron),
                cast(socio.c.numero_socio, String).like(patron),
                socio.c.nombre.ilike(patron),
                socio.c.apellido.ilike(patron),
            )
        )
    return [dict(fila) for fila in db.execute(consulta).mappings()]
