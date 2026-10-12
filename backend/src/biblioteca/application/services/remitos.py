"""Remitos: consultas y trazabilidad (solo lectura)."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from biblioteca.application.parametros import parametro_entero
from biblioteca.domain.enums import EstadoRemito, Sentido
from biblioteca.domain.errors import NoEncontrado
from biblioteca.infrastructure.db.tables import (
    ejemplar,
    libro,
    movimiento_remito,
    prestamo,
    remito,
    sede,
    socio,
    usuario,
)

origen = sede.alias("origen")
destino = sede.alias("destino")


def listar_remitos(
    db: Session,
    ahora: datetime,
    estado: EstadoRemito | None,
    sentido: Sentido | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    dias_max_transito = parametro_entero(db, "dias_max_transito")
    consulta = (
        select(
            remito.c.id,
            remito.c.numero,
            remito.c.sentido,
            remito.c.estado,
            remito.c.fecha_generacion,
            remito.c.fecha_despacho,
            remito.c.fecha_recepcion,
            remito.c.resultado_revision,
            remito.c.observacion_revision,
            remito.c.prestamo_id,
            ejemplar.c.codigo_inventario,
            libro.c.titulo,
            origen.c.nombre.label("sede_origen"),
            destino.c.nombre.label("sede_destino"),
            (socio.c.apellido + ", " + socio.c.nombre).label("socio"),
        )
        .join(ejemplar, remito.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(origen, remito.c.sede_origen_id == origen.c.id)
        .join(destino, remito.c.sede_destino_id == destino.c.id)
        .outerjoin(prestamo, remito.c.prestamo_id == prestamo.c.id)
        .outerjoin(socio, prestamo.c.socio_id == socio.c.id)
        .order_by(remito.c.fecha_generacion.desc())
        .limit(limit)
        .offset(offset)
    )
    if estado is not None:
        consulta = consulta.where(remito.c.estado == estado)
    if sentido is not None:
        consulta = consulta.where(remito.c.sentido == sentido)

    resultado = []
    for fila in db.execute(consulta).mappings():
        r = dict(fila)
        en_transito = r["estado"] == EstadoRemito.EN_TRANSITO
        r["dias_en_transito"] = (ahora - r["fecha_despacho"]).days if en_transito else None
        # `demorado` es derivado (ARCHITECTURE.md §4.3, Logística).
        r["demorado"] = en_transito and r["dias_en_transito"] > dias_max_transito
        resultado.append(r)
    return resultado


def movimientos_de_remito(db: Session, remito_id: int) -> list[dict[str, Any]]:
    """Historial de estados del remito: es su trazabilidad a lo largo del trayecto."""
    existe = db.execute(select(remito.c.id).where(remito.c.id == remito_id)).scalar()
    if existe is None:
        raise NoEncontrado(f"No existe el remito {remito_id}")

    consulta = (
        select(
            movimiento_remito.c.id,
            movimiento_remito.c.estado_anterior,
            movimiento_remito.c.estado_nuevo,
            movimiento_remito.c.fecha_hora,
            movimiento_remito.c.observacion,
            usuario.c.nombre_completo.label("usuario"),
        )
        .join(usuario, movimiento_remito.c.usuario_id == usuario.c.id)
        .where(movimiento_remito.c.remito_id == remito_id)
        .order_by(movimiento_remito.c.fecha_hora, movimiento_remito.c.id)
    )
    return [dict(fila) for fila in db.execute(consulta).mappings()]
