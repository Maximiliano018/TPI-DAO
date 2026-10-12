from types import TracebackType
from typing import Protocol, Self

from biblioteca.domain.repositories import SedeRepository, UsuarioRepository


class UnitOfWork(Protocol):
    """Una transacción por caso de uso (ARCHITECTURE.md §3).

    Uso en un servicio:

        with self.uow:
            sede = self.uow.sedes.obtener(sede_id)
            sede.reactivar()
            self.uow.commit()

    Si el bloque termina sin `commit()` (o con una excepción), los cambios se descartan.
    """

    @property
    def sedes(self) -> SedeRepository: ...

    @property
    def usuarios(self) -> UsuarioRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
