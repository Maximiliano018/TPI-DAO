"""R4 · Préstamos vencidos y multas acumuladas.

- Vencidos: préstamos `ACTIVO` con la fecha de vencimiento pasada, con sus días de atraso.
- Multas: suma de las `PENDIENTE` y de las `SALDADA`, por socio y por sede (la sede
  destino del préstamo, que es donde se devolvió). Importes en centavos.
"""

from datetime import date
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from biblioteca.domain.enums import EstadoMulta, EstadoPrestamo
from biblioteca.infrastructure.db.tables import ejemplar, libro, multa, prestamo, sede, socio

_nombre_socio = (socio.c.apellido + ", " + socio.c.nombre).label("socio")


def _sumar_monto(estado: EstadoMulta) -> Any:
    return func.coalesce(func.sum(case((multa.c.estado == estado, multa.c.monto), else_=0)), 0)


def vencidos_y_multas(db: Session, hoy: date) -> dict[str, Any]:
    consulta_vencidos = (
        select(
            prestamo.c.id,
            prestamo.c.fecha_inicio,
            prestamo.c.fecha_vencimiento,
            _nombre_socio,
            socio.c.numero_socio,
            libro.c.titulo,
            ejemplar.c.codigo_inventario,
            sede.c.nombre.label("sede"),
        )
        .join(socio, prestamo.c.socio_id == socio.c.id)
        .join(ejemplar, prestamo.c.ejemplar_id == ejemplar.c.id)
        .join(libro, ejemplar.c.libro_id == libro.c.id)
        .join(sede, prestamo.c.sede_destino_id == sede.c.id)
        .where(prestamo.c.estado == EstadoPrestamo.ACTIVO, prestamo.c.fecha_vencimiento < hoy)
        .order_by(prestamo.c.fecha_vencimiento)
    )
    vencidos = []
    for fila in db.execute(consulta_vencidos).mappings():
        v = dict(fila)
        v["dias_atraso"] = (hoy - v["fecha_vencimiento"]).days
        vencidos.append(v)

    columnas_multas = (
        func.count(multa.c.id).label("cantidad"),
        _sumar_monto(EstadoMulta.PENDIENTE).label("pendiente"),
        _sumar_monto(EstadoMulta.SALDADA).label("saldado"),
    )
    multas_de_prestamos = multa.join(prestamo, multa.c.prestamo_id == prestamo.c.id)

    por_socio = [
        dict(fila)
        for fila in db.execute(
            select(socio.c.id.label("socio_id"), _nombre_socio, *columnas_multas)
            .select_from(multas_de_prestamos.join(socio, prestamo.c.socio_id == socio.c.id))
            .group_by(socio.c.id)
            .order_by(_sumar_monto(EstadoMulta.PENDIENTE).desc(), socio.c.apellido)
        ).mappings()
    ]
    por_sede = [
        dict(fila)
        for fila in db.execute(
            select(sede.c.id.label("sede_id"), sede.c.nombre.label("sede"), *columnas_multas)
            .select_from(multas_de_prestamos.join(sede, prestamo.c.sede_destino_id == sede.c.id))
            .group_by(sede.c.id)
            .order_by(sede.c.nombre)
        ).mappings()
    ]

    return {
        "vencidos": vencidos,
        "multas_por_socio": por_socio,
        "multas_por_sede": por_sede,
        "total_pendiente": sum(s["pendiente"] for s in por_socio),
        "total_saldado": sum(s["saldado"] for s in por_socio),
    }
