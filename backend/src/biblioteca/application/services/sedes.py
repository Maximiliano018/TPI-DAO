"""Sedes: consultas.

Las consultas de este paquete son de solo lectura y van directo a las tablas. Los casos de
uso que modifican datos (alta, baja, préstamos, envíos...) van a pasar por las entidades
del dominio y sus repositorios (ARCHITECTURE.md §3).
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from biblioteca.domain.enums import EstadoEjemplar
from biblioteca.infrastructure.db.tables import ejemplar, horario_sede, sede


def listar_sedes(db: Session) -> list[dict[str, Any]]:
    ejemplares = (
        select(func.count())
        .where(ejemplar.c.sede_id == sede.c.id, ejemplar.c.estado != EstadoEjemplar.BAJA)
        .scalar_subquery()
    )
    sedes = [
        dict(fila)
        for fila in db.execute(
            select(sede, ejemplares.label("cantidad_ejemplares")).order_by(sede.c.nombre)
        ).mappings()
    ]

    horarios: dict[int, list[dict[str, Any]]] = {}
    consulta_horarios = select(horario_sede).order_by(
        horario_sede.c.dia_semana, horario_sede.c.hora_apertura
    )
    for h in db.execute(consulta_horarios).mappings():
        horarios.setdefault(h["sede_id"], []).append(
            {
                "dia_semana": h["dia_semana"],
                "hora_apertura": h["hora_apertura"],
                "hora_cierre": h["hora_cierre"],
            }
        )

    for s in sedes:
        s["horarios"] = horarios.get(s["id"], [])
    return sedes
