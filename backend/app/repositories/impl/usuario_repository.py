"""Repositorio de usuarios sobre SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UsuarioORM
from app.models.usuario import Rol, SedeRef, Usuario


def a_dominio(orm: UsuarioORM) -> Usuario:
    """Convierte la fila ORM en la entidad de dominio."""
    sede = SedeRef(orm.sede.id, orm.sede.codigo, orm.sede.nombre) if orm.sede else None
    return Usuario(
        id=orm.id,
        username=orm.username,
        nombre=orm.nombre,
        rol=Rol(orm.rol),
        activo=orm.activo,
        sede=sede,
        socio_id=orm.socio_id,
        password_hash=orm.password_hash,
    )


class SqlAlchemyUsuarioRepository:
    """Implementa ``UsuarioRepository`` con SQLAlchemy."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def obtener(self, usuario_id: int) -> Usuario | None:
        orm = self._sesion.get(UsuarioORM, usuario_id)
        return a_dominio(orm) if orm else None

    def obtener_por_username(self, username: str) -> Usuario | None:
        orm = self._sesion.scalar(select(UsuarioORM).where(UsuarioORM.username == username))
        return a_dominio(orm) if orm else None
