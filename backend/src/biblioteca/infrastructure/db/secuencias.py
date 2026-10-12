"""Numeración correlativa (número de socio, código de inventario, número de remito).

Se incrementa dentro de la transacción de quien la pide: si esa transacción se
revierte, el número no se consume. Ver ARCHITECTURE.md §5.4.
"""

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from biblioteca.infrastructure.db.tables import secuencia

SECUENCIA_SOCIO = "socio"


def secuencia_inventario(codigo_sede: str) -> str:
    return f"inventario:{codigo_sede}"


def secuencia_remito(anio: int) -> str:
    return f"remito:{anio}"


def formatear_codigo_inventario(codigo_sede: str, numero: int) -> str:
    return f"{codigo_sede}-{numero:06d}"


def formatear_numero_remito(anio: int, numero: int) -> str:
    return f"R-{anio}-{numero:06d}"


def siguiente_valor(conn: Connection, nombre: str) -> int:
    """Devuelve el próximo valor de la secuencia, creándola si no existe."""
    valor = conn.execute(
        update(secuencia)
        .where(secuencia.c.nombre == nombre)
        .values(ultimo_valor=secuencia.c.ultimo_valor + 1)
        .returning(secuencia.c.ultimo_valor)
    ).scalar_one_or_none()
    if valor is not None:
        return int(valor)
    conn.execute(insert(secuencia).values(nombre=nombre, ultimo_valor=1))
    return 1
