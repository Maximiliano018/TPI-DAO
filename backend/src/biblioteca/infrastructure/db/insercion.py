from typing import Any

from sqlalchemy import Table, insert
from sqlalchemy.engine import Connection


def insertar(conn: Connection, tabla: Table, **valores: Any) -> int:
    """Inserta una fila y devuelve su id."""
    clave = conn.execute(insert(tabla).values(**valores)).inserted_primary_key
    if clave is None:
        raise RuntimeError(f"La inserción en {tabla.name} no devolvió una clave primaria")
    return int(clave[0])
