"""R5 · Disponibilidad del catálogo por sede.

Cuenta los ejemplares de cada libro en cada sede propietaria, agrupados por estado. Los
de consulta en sala (`prestable = false`) se cuentan aparte: nunca están "disponibles"
para préstamo.
"""

from typing import Any

from sqlalchemy import ColumnElement, and_, func, not_, or_, select
from sqlalchemy.orm import Session

from biblioteca.application.reports.comun import contar_si
from biblioteca.domain.enums import EstadoEjemplar
from biblioteca.infrastructure.db.tables import ejemplar, libro, sede

_prestable = ejemplar.c.prestable.is_(True)


def _contar_estados(*estados: EstadoEjemplar) -> ColumnElement[int]:
    return contar_si(and_(_prestable, ejemplar.c.estado.in_(estados)))


def disponibilidad(db: Session, buscar: str | None, sede_id: int | None) -> list[dict[str, Any]]:
    consulta = (
        select(
            libro.c.id.label("libro_id"),
            libro.c.titulo,
            libro.c.isbn,
            sede.c.id.label("sede_id"),
            sede.c.nombre.label("sede"),
            sede.c.activa.label("sede_activa"),
            func.count().label("total"),
            _contar_estados(EstadoEjemplar.DISPONIBLE).label("disponibles"),
            _contar_estados(EstadoEjemplar.PRESTADO).label("prestados"),
            _contar_estados(EstadoEjemplar.RESERVADO).label("reservados"),
            _contar_estados(EstadoEjemplar.PENDIENTE_DESPACHO, EstadoEjemplar.EN_TRANSITO).label(
                "en_transito"
            ),
            _contar_estados(EstadoEjemplar.EN_REVISION).label("en_revision"),
            contar_si(not_(_prestable)).label("consulta_en_sala"),
        )
        .select_from(
            ejemplar.join(libro, ejemplar.c.libro_id == libro.c.id).join(
                sede, ejemplar.c.sede_id == sede.c.id
            )
        )
        .where(ejemplar.c.estado != EstadoEjemplar.BAJA)
        .group_by(libro.c.id, sede.c.id)
        .order_by(libro.c.titulo, sede.c.nombre)
    )
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(or_(libro.c.titulo.ilike(patron), libro.c.isbn.like(patron)))
    if sede_id is not None:
        consulta = consulta.where(sede.c.id == sede_id)

    # Se agrupa por libro: cada libro con el detalle de cada sede.
    libros: dict[int, dict[str, Any]] = {}
    for fila in db.execute(consulta).mappings():
        item = libros.setdefault(
            fila["libro_id"],
            {
                "libro_id": fila["libro_id"],
                "titulo": fila["titulo"],
                "isbn": fila["isbn"],
                "disponibles": 0,
                "sedes": [],
            },
        )
        item["disponibles"] += fila["disponibles"]
        item["sedes"].append(
            {k: fila[k] for k in fila.keys() if k not in ("libro_id", "titulo", "isbn")}
        )
    return list(libros.values())
