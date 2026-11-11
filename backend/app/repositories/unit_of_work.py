"""Unit of Work: una transacción por caso de uso."""

from typing import Protocol

from sqlalchemy.orm import Session

from app.repositories.interfaces.usuario_repository import UsuarioRepository


class UnitOfWork(Protocol):
    """Agrupa los repositorios de una transacción."""

    usuarios: UsuarioRepository

    def commit(self) -> None:
        """Confirma la transacción."""
        ...

    def rollback(self) -> None:
        """Deshace la transacción."""
        ...


class SqlAlchemyUnitOfWork:
    """Unit of Work sobre una sesión de SQLAlchemy (una por solicitud)."""

    def __init__(self, sesion: Session) -> None:
        from app.repositories.impl.usuario_repository import SqlAlchemyUsuarioRepository

        self.sesion = sesion
        self.usuarios: UsuarioRepository = SqlAlchemyUsuarioRepository(sesion)

    def commit(self) -> None:
        self.sesion.commit()

    def rollback(self) -> None:
        self.sesion.rollback()
