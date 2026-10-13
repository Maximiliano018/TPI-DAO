"""R3 · Libros más solicitados en préstamos inter-sedes.

Un préstamo es inter-sedes si su sede origen difiere de la destino (el tipo se deriva,
no se guarda). Se cuentan todos los pedidos del período, incluidos los cancelados: miden
demanda, no préstamos concretados.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from biblioteca.application.alcance import involucra_sede
from biblioteca.application.reports.comun import filtro_periodo
from biblioteca.infrastructure.db.tables import ejemplar, libro, prestamo


def libros_mas_solicitados(
    db: Session, desde: date | None, hasta: date | None, limite: int, *, sede_id: int | None
) -> list[dict[str, Any]]:
    """Con `sede_id`, solo los pedidos donde la sede presta o recibe el libro."""
    solicitudes = func.count(prestamo.c.id)
    consulta = (
        select(
            libro.c.id.label("libro_id"),
            libro.c.titulo,
            libro.c.isbn,
            solicitudes.label("solicitudes"),
            func.count(func.distinct(prestamo.c.socio_id)).label("socios"),
            func.count(func.distinct(prestamo.c.sede_destino_id)).label("sedes_destino"),
        )
        .join(ejemplar, prestamo.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .where(
            prestamo.c.sede_origen_id != prestamo.c.sede_destino_id,
            *filtro_periodo(prestamo.c.fecha_solicitud, desde, hasta),
            *involucra_sede(sede_id, prestamo.c.sede_origen_id, prestamo.c.sede_destino_id),
        )
        .group_by(libro.c.id)
        .order_by(solicitudes.desc(), libro.c.titulo)
        .limit(limite)
    )
    return [dict(fila) for fila in db.execute(consulta).mappings()]
