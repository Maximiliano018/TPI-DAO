import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from biblioteca.api.deps import get_db
from biblioteca.infrastructure.db.migraciones import aplicar_migraciones
from biblioteca.infrastructure.db.seed import cargar_datos_iniciales, cargar_demo
from biblioteca.infrastructure.db.session import crear_engine
from biblioteca.main import app


@pytest.fixture(scope="session")
def base_demo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Base migrada con los datos de demostración. Los tests de consulta no la modifican."""
    ruta = tmp_path_factory.mktemp("demo") / "demo.db"
    url = f"sqlite:///{ruta}"
    aplicar_migraciones(url)
    engine = crear_engine(url)
    with engine.begin() as conn:
        cargar_datos_iniciales(conn)
        cargar_demo(conn)
    engine.dispose()
    return ruta


@contextmanager
def _cliente_sobre(ruta: Path) -> Iterator[TestClient]:
    """Cliente HTTP cuya sesión de base apunta al archivo indicado."""
    engine = crear_engine(f"sqlite:///{ruta}")
    sesiones = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_prueba() -> Iterator[Session]:
        db = sesiones()
        try:
            yield db
        finally:
            db.close()

    anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = db_de_prueba
    try:
        with TestClient(app) as c:
            yield c
    finally:
        if anterior is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = anterior
        engine.dispose()


@pytest.fixture(scope="session")
def cliente(base_demo: Path) -> Iterator[TestClient]:
    """Para consultas: comparte una sola base de demostración."""
    with _cliente_sobre(base_demo) as c:
        yield c


@pytest.fixture
def cliente_escritura(base_demo: Path, tmp_path: Path) -> Iterator[TestClient]:
    """Para tests que modifican datos: cada uno trabaja sobre su propia copia de la demo."""
    copia = tmp_path / "demo.db"
    shutil.copy(base_demo, copia)
    with _cliente_sobre(copia) as c:
        yield c
