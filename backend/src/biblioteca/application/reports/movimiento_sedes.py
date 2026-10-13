"""R1 · Movimiento de ejemplares entre sedes y tiempo promedio de tránsito.

Agrupa los remitos (sin los cancelados) por ruta origen → destino. El tiempo de tránsito
es `fecha_recepcion - fecha_despacho` de los remitos recibidos; se promedia en Python
para no depender de funciones de fecha propias de SQLite.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.application.reports.comun import contar_si, filtro_periodo
from biblioteca.domain.enums import ESTADOS_REMITO_NO_FINALES, EstadoRemito
from biblioteca.infrastructure.db.tables import remito, sede

origen = sede.alias("origen")
destino = sede.alias("destino")

_SEGUNDOS_POR_DIA = 86_400


def movimiento_entre_sedes(
    db: Session, desde: date | None, hasta: date | None, *, sede_id: int | None
) -> dict[str, Any]:
    """Con `sede_id`, solo las rutas que salen de la sede o llegan a ella."""
    filtros = [
        remito.c.estado != EstadoRemito.CANCELADO,
        *filtro_periodo(remito.c.fecha_generacion, desde, hasta),
        *involucra_sede(sede_id, remito.c.sede_origen_id, remito.c.sede_destino_id),
    ]

    consulta = (
        select(
            origen.c.id.label("sede_origen_id"),
            origen.c.nombre.label("sede_origen"),
            destino.c.id.label("sede_destino_id"),
            destino.c.nombre.label("sede_destino"),
            func.count().label("envios"),
            contar_si(remito.c.estado == EstadoRemito.RECIBIDO).label("recibidos"),
            contar_si(remito.c.estado.in_(ESTADOS_REMITO_NO_FINALES)).label("en_curso"),
            contar_si(remito.c.estado == EstadoRemito.EXTRAVIADO).label("extraviados"),
        )
        .join(origen, remito.c.sede_origen_id == origen.c.id)
        .join(destino, remito.c.sede_destino_id == destino.c.id)
        .where(*filtros)
        .group_by(origen.c.id, destino.c.id)
        .order_by(func.count().desc(), origen.c.nombre, destino.c.nombre)
    )
    rutas = [dict(fila) for fila in db.execute(consulta).mappings()]

    # Duraciones de los viajes completos, por ruta.
    duraciones: dict[tuple[int, int], list[float]] = {}
    consulta_tiempos = select(
        remito.c.sede_origen_id,
        remito.c.sede_destino_id,
        remito.c.fecha_despacho,
        remito.c.fecha_recepcion,
    ).where(*filtros, remito.c.estado == EstadoRemito.RECIBIDO)
    for origen_id, destino_id, despacho, recepcion in db.execute(consulta_tiempos):
        dias = (recepcion - despacho).total_seconds() / _SEGUNDOS_POR_DIA
        duraciones.setdefault((origen_id, destino_id), []).append(dias)

    for ruta in rutas:
        tiempos = duraciones.get((ruta["sede_origen_id"], ruta["sede_destino_id"]), [])
        ruta["dias_promedio_transito"] = round(sum(tiempos) / len(tiempos), 1) if tiempos else None

    todos = [d for lista in duraciones.values() for d in lista]
    return {
        "envios_totales": sum(r["envios"] for r in rutas),
        "dias_promedio_transito": round(sum(todos) / len(todos), 1) if todos else None,
        "rutas": rutas,
    }
