"""Unit of Work: una transacción por caso de uso."""

from typing import Protocol

from sqlalchemy.orm import Session

from app.repositories.interfaces.catalogo_repository import (
    CategoriaRepository,
    EjemplarRepository,
    LibroRepository,
)
from app.repositories.interfaces.prestamo_repository import (
    IncidenciaRepository,
    ParametroRepository,
    PrestamoRepository,
    RemitoRepository,
    ReservaRepository,
)
from app.repositories.interfaces.sede_repository import LocalidadRepository, SedeRepository
from app.repositories.interfaces.socio_repository import SocioRepository
from app.repositories.interfaces.usuario_repository import UsuarioRepository


class UnitOfWork(Protocol):
    """Agrupa los repositorios de una transacción."""

    usuarios: UsuarioRepository
    sedes: SedeRepository
    localidades: LocalidadRepository
    socios: SocioRepository
    categorias: CategoriaRepository
    libros: LibroRepository
    ejemplares: EjemplarRepository
    parametros: ParametroRepository
    prestamos: PrestamoRepository
    remitos: RemitoRepository
    incidencias: IncidenciaRepository
    reservas: ReservaRepository

    def commit(self) -> None:
        """Confirma la transacción."""
        ...

    def rollback(self) -> None:
        """Deshace la transacción."""
        ...


class SqlAlchemyUnitOfWork:
    """Unit of Work sobre una sesión de SQLAlchemy (una por solicitud)."""

    def __init__(self, sesion: Session) -> None:
        from app.repositories.impl.catalogo_repository import (
            SqlAlchemyCategoriaRepository,
            SqlAlchemyEjemplarRepository,
            SqlAlchemyLibroRepository,
        )
        from app.repositories.impl.prestamo_repository import (
            SqlAlchemyIncidenciaRepository,
            SqlAlchemyParametroRepository,
            SqlAlchemyPrestamoRepository,
            SqlAlchemyRemitoRepository,
        )
        from app.repositories.impl.reserva_repository import SqlAlchemyReservaRepository
        from app.repositories.impl.sede_repository import (
            SqlAlchemyLocalidadRepository,
            SqlAlchemySedeRepository,
        )
        from app.repositories.impl.socio_repository import SqlAlchemySocioRepository
        from app.repositories.impl.usuario_repository import SqlAlchemyUsuarioRepository

        self.sesion = sesion
        self.usuarios: UsuarioRepository = SqlAlchemyUsuarioRepository(sesion)
        self.sedes: SedeRepository = SqlAlchemySedeRepository(sesion)
        self.localidades: LocalidadRepository = SqlAlchemyLocalidadRepository(sesion)
        self.socios: SocioRepository = SqlAlchemySocioRepository(sesion)
        self.categorias: CategoriaRepository = SqlAlchemyCategoriaRepository(sesion)
        self.libros: LibroRepository = SqlAlchemyLibroRepository(sesion)
        self.ejemplares: EjemplarRepository = SqlAlchemyEjemplarRepository(sesion)
        self.parametros: ParametroRepository = SqlAlchemyParametroRepository(sesion)
        self.prestamos: PrestamoRepository = SqlAlchemyPrestamoRepository(sesion)
        self.remitos: RemitoRepository = SqlAlchemyRemitoRepository(sesion)
        self.incidencias: IncidenciaRepository = SqlAlchemyIncidenciaRepository(sesion)
        self.reservas: ReservaRepository = SqlAlchemyReservaRepository(sesion)

    def commit(self) -> None:
        self.sesion.commit()

    def rollback(self) -> None:
        self.sesion.rollback()
