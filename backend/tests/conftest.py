import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from biblioteca.infrastructure.db.migraciones import aplicar_migraciones
from biblioteca.infrastructure.db.session import crear_engine
from biblioteca.infrastructure.repositories.unidad_de_trabajo import SqlUnidadDeTrabajo


@pytest.fixture(scope="session")
def base_migrada(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Base creada con las migraciones de Alembic, una sola vez por sesión de tests."""
    ruta = tmp_path_factory.mktemp("plantilla") / "plantilla.db"
    aplicar_migraciones(f"sqlite:///{ruta}")
    return ruta


@pytest.fixture
def ruta_base(base_migrada: Path, tmp_path: Path) -> Path:
    """Copia de la base migrada: cada test arranca con un esquema limpio."""
    ruta = tmp_path / "test.db"
    shutil.copy(base_migrada, ruta)
    return ruta


@pytest.fixture
def engine(ruta_base: Path) -> Iterator[Engine]:
    engine = crear_engine(f"sqlite:///{ruta_base}")
    yield engine
    engine.dispose()


@pytest.fixture
def nueva_uow(engine: Engine) -> Iterator[Callable[[], SqlUnidadDeTrabajo]]:
    """Fábrica de unidades de trabajo, cada una con su propia sesión (como un request).

    Usar una nueva para leer lo que otra confirmó: así se prueba lo que quedó en la base
    y no lo que quedó en memoria.
    """
    sesiones = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    abiertas: list[Session] = []

    def crear() -> SqlUnidadDeTrabajo:
        abiertas.append(sesiones())
        return SqlUnidadDeTrabajo(abiertas[-1])

    yield crear
    for session in abiertas:
        session.close()
