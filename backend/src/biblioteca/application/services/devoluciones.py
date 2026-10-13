"""Devoluciones: consultas (solo lectura)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.infrastructure.db.tables import (
    devolucion,
    ejemplar,
    libro,
    multa,
    prestamo,
    sede,
    socio,
    usuario,
)


def listar_devoluciones(
    db: Session, limit: int, offset: int, *, sede_id: int | None
) -> list[dict[str, Any]]:
    """Con `sede_id`, solo las de préstamos donde la sede es origen o destino."""
    consulta = (
        select(
            devolucion.c.id,
            devolucion.c.fecha_hora,
            devolucion.c.condicion_fisica,
            devolucion.c.observacion,
            prestamo.c.id.label("prestamo_id"),
            prestamo.c.fecha_vencimiento,
            (socio.c.apellido + ", " + socio.c.nombre).label("socio"),
            libro.c.titulo,
            ejemplar.c.codigo_inventario,
            sede.c.nombre.label("sede"),
            usuario.c.nombre_completo.label("registrado_por"),
            multa.c.dias_atraso,
            multa.c.monto.label("multa_monto"),
            multa.c.estado.label("multa_estado"),
        )
        .join(prestamo, devolucion.c.prestamo_id == prestamo.c.id)
        .join(socio, prestamo.c.socio_id == socio.c.id)
        .join(ejemplar, prestamo.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        # Se devuelve en la sede destino del préstamo (ARCHITECTURE.md §4.3).
        .join(sede, prestamo.c.sede_destino_id == sede.c.id)
        .join(usuario, devolucion.c.registrado_por == usuario.c.id)
        .outerjoin(multa, multa.c.prestamo_id == prestamo.c.id)
        .where(*involucra_sede(sede_id, prestamo.c.sede_origen_id, prestamo.c.sede_destino_id))
        .order_by(devolucion.c.fecha_hora.desc())
        .limit(limit)
        .offset(offset)
    )
    return [dict(fila) for fila in db.execute(consulta).mappings()]
