"""Piezas de consulta compartidas por los repositorios SQLAlchemy."""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.db.models import UsuarioORM

_CON_TILDES = "áéíóúüàèìòùâêîôûñ"
_SIN_TILDES = "aeiouuaeiouaeioun"


def sin_tildes(columna: Any) -> ColumnElement[str]:
    """Minúsculas y sin tildes en SQL, igual que ``utils.texto.normalizar`` para letras."""
    return func.translate(func.lower(columna), _CON_TILDES, _SIN_TILDES)


def nombres_de_usuarios(sesion: Session, ids: Iterable[int]) -> dict[int, str]:
    """Nombres para mostrar de los usuarios indicados (una sola consulta)."""
    pedidos = set(ids)
    if not pedidos:
        return {}
    filas = sesion.execute(
        select(UsuarioORM.id, UsuarioORM.nombre).where(UsuarioORM.id.in_(pedidos))
    )
    return {fila.id: fila.nombre for fila in filas}
