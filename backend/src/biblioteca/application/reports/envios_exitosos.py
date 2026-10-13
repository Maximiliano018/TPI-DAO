"""R2 · Tasa de envíos exitosos e incidencias.

Sobre los remitos finalizados y no cancelados (`RECIBIDO` o `EXTRAVIADO`): exitoso es el
recibido con revisión `CONFORME`; incidencias son los dañados, destruidos y extraviados.
Se desglosa por sede de origen del envío.
"""

from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.application.reports.comun import contar_si, filtro_periodo
from biblioteca.domain.enums import EstadoRemito, ResultadoRevision
from biblioteca.infrastructure.db.tables import remito, sede


def _recibido_con(resultado: ResultadoRevision) -> ColumnElement[bool]:
    return and_(remito.c.estado == EstadoRemito.RECIBIDO, remito.c.resultado_revision == resultado)


def _tasa(exitosos: int, total: int) -> float | None:
    return round(100 * exitosos / total, 1) if total else None


def envios_exitosos(
    db: Session, desde: date | None, hasta: date | None, *, sede_id: int | None
) -> dict[str, Any]:
    """Con `sede_id`, solo los envíos que salen de la sede o llegan a ella."""
    consulta = (
        select(
            sede.c.id.label("sede_id"),
            sede.c.nombre.label("sede"),
            func.count().label("total"),
            contar_si(_recibido_con(ResultadoRevision.CONFORME)).label("exitosos"),
            contar_si(_recibido_con(ResultadoRevision.DANADO)).label("danados"),
            contar_si(_recibido_con(ResultadoRevision.DESTRUIDO)).label("destruidos"),
            contar_si(remito.c.estado == EstadoRemito.EXTRAVIADO).label("extraviados"),
        )
        .join(sede, remito.c.sede_origen_id == sede.c.id)
        .where(
            remito.c.estado.in_((EstadoRemito.RECIBIDO, EstadoRemito.EXTRAVIADO)),
            *filtro_periodo(remito.c.fecha_generacion, desde, hasta),
            *involucra_sede(sede_id, remito.c.sede_origen_id, remito.c.sede_destino_id),
        )
        .group_by(sede.c.id)
        .order_by(sede.c.nombre)
    )
    por_sede = [dict(fila) for fila in db.execute(consulta).mappings()]
    for s in por_sede:
        s["incidencias"] = s["danados"] + s["destruidos"] + s["extraviados"]
        s["tasa_exito"] = _tasa(s["exitosos"], s["total"])

    total = sum(s["total"] for s in por_sede)
    exitosos = sum(s["exitosos"] for s in por_sede)
    return {
        "total": total,
        "exitosos": exitosos,
        "tasa_exito": _tasa(exitosos, total),
        "incidencias": {
            "danados": sum(s["danados"] for s in por_sede),
            "destruidos": sum(s["destruidos"] for s in por_sede),
            "extraviados": sum(s["extraviados"] for s in por_sede),
        },
        "por_sede": por_sede,
    }
