"""Tablero: préstamos activos, material en tránsito y alertas (reporte R6)."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from biblioteca.application.parametros import parametro_entero
from biblioteca.domain.enums import EstadoMulta, EstadoPrestamo, EstadoRemito, EstadoReserva
from biblioteca.infrastructure.db.tables import (
    ejemplar,
    libro,
    movimiento_remito,
    multa,
    prestamo,
    remito,
    reserva,
    sede,
    socio,
    usuario,
)

DIAS_PROXIMOS_VENCIMIENTOS = 7


def resumen(db: Session, ahora: datetime) -> dict[str, Any]:
    hoy = ahora.date()

    prestamos_por_estado = {
        e: n
        for e, n in db.execute(select(prestamo.c.estado, func.count()).group_by(prestamo.c.estado))
    }
    reservas_por_estado = {
        e: n
        for e, n in db.execute(select(reserva.c.estado, func.count()).group_by(reserva.c.estado))
    }
    vencidos = db.execute(
        select(func.count()).where(
            prestamo.c.estado == EstadoPrestamo.ACTIVO, prestamo.c.fecha_vencimiento < hoy
        )
    ).scalar_one()

    dias_max_transito = parametro_entero(db, "dias_max_transito")
    despachos = (
        db.execute(
            select(remito.c.fecha_despacho).where(remito.c.estado == EstadoRemito.EN_TRANSITO)
        )
        .scalars()
        .all()
    )
    demorados = sum(1 for d in despachos if (ahora - d).days > dias_max_transito)

    multas_pendientes = db.execute(
        select(func.count(), func.coalesce(func.sum(multa.c.monto), 0)).where(
            multa.c.estado == EstadoMulta.PENDIENTE
        )
    ).one()

    return {
        "prestamos_activos": prestamos_por_estado.get(EstadoPrestamo.ACTIVO, 0),
        "prestamos_vencidos": vencidos,
        "prestamos_en_envio": prestamos_por_estado.get(EstadoPrestamo.EN_ENVIO, 0),
        "listos_para_retiro": prestamos_por_estado.get(EstadoPrestamo.LISTO_PARA_RETIRO, 0),
        "remitos_en_transito": len(despachos),
        "remitos_demorados": demorados,
        "reservas_pendientes": reservas_por_estado.get(EstadoReserva.PENDIENTE, 0),
        "reservas_asignadas": reservas_por_estado.get(EstadoReserva.ASIGNADA, 0),
        "multas_pendientes": multas_pendientes[0],
        "multas_pendientes_monto": multas_pendientes[1],
        "proximos_vencimientos": _proximos_vencimientos(db, ahora),
        "ultimos_movimientos": _ultimos_movimientos(db),
    }


def _proximos_vencimientos(db: Session, ahora: datetime) -> list[dict[str, Any]]:
    """Préstamos activos vencidos o que vencen en los próximos días."""
    hoy = ahora.date()
    consulta = (
        select(
            prestamo.c.id,
            prestamo.c.fecha_vencimiento,
            (socio.c.apellido + ", " + socio.c.nombre).label("socio"),
            libro.c.titulo,
            sede.c.nombre.label("sede"),
        )
        .join(socio, prestamo.c.socio_id == socio.c.id)
        .join(ejemplar, prestamo.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(sede, prestamo.c.sede_destino_id == sede.c.id)
        .where(
            prestamo.c.estado == EstadoPrestamo.ACTIVO,
            prestamo.c.fecha_vencimiento <= hoy + timedelta(DIAS_PROXIMOS_VENCIMIENTOS),
        )
        .order_by(prestamo.c.fecha_vencimiento)
    )
    resultado = []
    for fila in db.execute(consulta).mappings():
        p = dict(fila)
        p["dias_restantes"] = (p["fecha_vencimiento"] - hoy).days
        resultado.append(p)
    return resultado


def _ultimos_movimientos(db: Session, cantidad: int = 8) -> list[dict[str, Any]]:
    consulta = (
        select(
            movimiento_remito.c.id,
            movimiento_remito.c.estado_nuevo,
            movimiento_remito.c.fecha_hora,
            remito.c.id.label("remito_id"),
            remito.c.numero,
            libro.c.titulo,
            usuario.c.nombre_completo.label("usuario"),
        )
        .join(remito, movimiento_remito.c.remito_id == remito.c.id)
        .join(ejemplar, remito.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(usuario, movimiento_remito.c.usuario_id == usuario.c.id)
        .order_by(movimiento_remito.c.fecha_hora.desc(), movimiento_remito.c.id.desc())
        .limit(cantidad)
    )
    return [dict(fila) for fila in db.execute(consulta).mappings()]
