import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from biblioteca.infrastructure.db.migraciones import aplicar_migraciones
from biblioteca.infrastructure.db.session import crear_engine
from biblioteca.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture(scope="session")
def base_migrada(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Base creada con las migraciones de Alembic, una sola vez por sesión de tests."""
    ruta = tmp_path_factory.mktemp("plantilla") / "plantilla.db"
    aplicar_migraciones(f"sqlite:///{ruta}")
    return ruta


@pytest.fixture
def engine(base_migrada: Path, tmp_path: Path) -> Iterator[Engine]:
    """Copia de la base migrada: cada test arranca con un esquema limpio."""
    ruta = tmp_path / "test.db"
    shutil.copy(base_migrada, ruta)
    engine = crear_engine(f"sqlite:///{ruta}")
    yield engine
    engine.dispose()


@pytest.fixture
def uow(engine: Engine) -> SqlAlchemyUnitOfWork:
    """Unidad de Trabajo real sobre la base del test."""
    return SqlAlchemyUnitOfWork(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
