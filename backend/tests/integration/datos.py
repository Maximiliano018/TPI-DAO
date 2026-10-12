"""Inserciones mínimas válidas para armar escenarios en los tests de base de datos.

Cada función acepta `**campos` para pisar valores y provocar el caso a probar.
"""

from datetime import UTC, date, datetime
from itertools import count
from typing import Any

from sqlalchemy import Table
from sqlalchemy.engine import Connection

from biblioteca.domain.enums import EstadoPrestamo, Rol, Sentido
from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.db.insercion import insertar

_correlativo = count(1)
AHORA = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)
HOY = date(2026, 10, 12)


def _insertar(conn: Connection, tabla: Table, valores: dict[str, Any]) -> int:
    return insertar(conn, tabla, **valores)


def sede(conn: Connection, **campos: Any) -> int:
    n = next(_correlativo)
    valores = {
        "codigo": f"S{n:02d}",
        "nombre": f"Sede {n}",
        "direccion": "Calle 1",
        "localidad": "Córdoba",
    }
    return _insertar(conn, t.sede, valores | campos)


def usuario(conn: Connection, sede_id: int | None, **campos: Any) -> int:
    n = next(_correlativo)
    valores = {
        "username": f"usuario{n}",
        "nombre_completo": f"Usuario {n}",
        "password_hash": "hash",
        "rol": Rol.BIBLIOTECARIO if sede_id is not None else Rol.ADMIN,
        "sede_id": sede_id,
    }
    return _insertar(conn, t.usuario, valores | campos)


def libro(conn: Connection, **campos: Any) -> int:
    n = next(_correlativo)
    valores = {"isbn": f"978{n:010d}", "titulo": f"Libro {n}"}
    return _insertar(conn, t.libro, valores | campos)


def ejemplar(conn: Connection, libro_id: int, sede_id: int, **campos: Any) -> int:
    n = next(_correlativo)
    valores = {
        "codigo_inventario": f"EJ-{n:06d}",
        "libro_id": libro_id,
        "sede_id": sede_id,
        "fecha_alta": HOY,
    }
    return _insertar(conn, t.ejemplar, valores | campos)


def socio(conn: Connection, **campos: Any) -> int:
    n = next(_correlativo)
    valores = {
        "numero_socio": n,
        "dni": f"{20000000 + n}",
        "nombre": "Nombre",
        "apellido": "Apellido",
        "fecha_alta": HOY,
    }
    return _insertar(conn, t.socio, valores | campos)


def prestamo(
    conn: Connection,
    *,
    socio_id: int,
    ejemplar_id: int,
    sede_origen_id: int,
    sede_destino_id: int,
    registrado_por: int,
    **campos: Any,
) -> int:
    """Por defecto, un préstamo local ACTIVO."""
    valores = {
        "socio_id": socio_id,
        "ejemplar_id": ejemplar_id,
        "sede_origen_id": sede_origen_id,
        "sede_destino_id": sede_destino_id,
        "estado": EstadoPrestamo.ACTIVO,
        "fecha_solicitud": AHORA,
        "fecha_inicio": HOY,
        "fecha_vencimiento": date(2026, 10, 26),
        "registrado_por": registrado_por,
    }
    return _insertar(conn, t.prestamo, valores | campos)


def remito(
    conn: Connection,
    *,
    ejemplar_id: int,
    sede_origen_id: int,
    sede_destino_id: int,
    prestamo_id: int | None = None,
    **campos: Any,
) -> int:
    """Por defecto, un remito de IDA en estado GENERADO."""
    n = next(_correlativo)
    valores = {
        "numero": f"R-2026-{n:06d}",
        "ejemplar_id": ejemplar_id,
        "prestamo_id": prestamo_id,
        "sentido": Sentido.IDA,
        "sede_origen_id": sede_origen_id,
        "sede_destino_id": sede_destino_id,
        "fecha_generacion": AHORA,
    }
    return _insertar(conn, t.remito, valores | campos)


def reserva(
    conn: Connection,
    *,
    socio_id: int,
    libro_id: int,
    sede_id: int,
    registrado_por: int,
    **campos: Any,
) -> int:
    valores = {
        "socio_id": socio_id,
        "libro_id": libro_id,
        "sede_id": sede_id,
        "fecha_solicitud": AHORA,
        "registrado_por": registrado_por,
    }
    return _insertar(conn, t.reserva, valores | campos)
