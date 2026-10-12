from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from biblioteca.infrastructure.db.mappers import configurar_mapeos
from biblioteca.infrastructure.repositories.sede_repository import SqlAlchemySedeRepository
from biblioteca.infrastructure.repositories.usuario_repository import (
    SqlAlchemyUsuarioRepository,
)


class SqlAlchemyUnitOfWork:
    """Abre una sesión por bloque `with` y la cierra al salir.

    Sin `commit()` explícito, todo lo hecho en el bloque se revierte. Los objetos
    devueltos siguen siendo legibles después (la sesión no los expira al confirmar).
    """

    sedes: SqlAlchemySedeRepository
    usuarios: SqlAlchemyUsuarioRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        configurar_mapeos()
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self.session = self._session_factory()
        self.sedes = SqlAlchemySedeRepository(self.session)
        self.usuarios = SqlAlchemyUsuarioRepository(self.session)
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        # `close()` descarta lo no confirmado sin expirar los objetos ya leídos, que el
        # servicio devuelve después del bloque. `rollback()` sí los expira: solo se usa
        # ante un error, cuando nadie va a leer esos objetos.
        if error is not None:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
