import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from biblioteca.api.deps import get_db, get_hasher, get_reloj
from biblioteca.application.services.usuarios import registrar_admin
from biblioteca.domain.entities.usuario import Usuario
from biblioteca.domain.enums import Rol
from biblioteca.infrastructure.db.migraciones import aplicar_migraciones
from biblioteca.infrastructure.db.seed import cargar_datos_iniciales, cargar_demo
from biblioteca.infrastructure.db.seed_circulacion import CONTRASENA_DEMO
from biblioteca.infrastructure.db.session import crear_engine
from biblioteca.infrastructure.repositories.unidad_de_trabajo import SqlUnidadDeTrabajo
from biblioteca.main import app
from tests import datos
from tests.apoyo import HasherDePrueba, RelojFijo

CONTRASENA = "contrasena-segura"


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
def _cliente_sobre(
    ruta: Path, overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None
) -> Iterator[TestClient]:
    """Cliente HTTP cuya sesión de base apunta al archivo indicado.

    `overrides` reemplaza otras dependencias (reloj, hasher) mientras dura el cliente.
    """
    engine = crear_engine(f"sqlite:///{ruta}")
    sesiones = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_prueba() -> Iterator[Session]:
        db = sesiones()
        try:
            yield db
        finally:
            db.close()

    reemplazos = {get_db: db_de_prueba, **(overrides or {})}
    anteriores = {dep: app.dependency_overrides.get(dep) for dep in reemplazos}
    app.dependency_overrides.update(reemplazos)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        for dep, anterior in anteriores.items():
            if anterior is None:
                app.dependency_overrides.pop(dep, None)
            else:
                app.dependency_overrides[dep] = anterior
        engine.dispose()


@pytest.fixture(scope="session")
def cliente(base_demo: Path) -> Iterator[TestClient]:
    """Para consultas: comparte una sola base de demostración, con sesión de ADMIN."""
    with _cliente_sobre(base_demo) as c:
        c.headers.update(login(c, "admin", CONTRASENA_DEMO))
        yield c


@pytest.fixture
def cliente_escritura(base_demo: Path, tmp_path: Path) -> Iterator[TestClient]:
    """Para tests que modifican datos: cada uno trabaja sobre su propia copia de la demo,
    con sesión de ADMIN."""
    copia = tmp_path / "demo.db"
    shutil.copy(base_demo, copia)
    with _cliente_sobre(copia) as c:
        c.headers.update(login(c, "admin", CONTRASENA_DEMO))
        yield c


# ----------------------------------------------------- Base vacía, con sesión y reloj fijo


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def cliente_limpio(ruta_base: Path, reloj: RelojFijo) -> Iterator[TestClient]:
    """Base migrada sin datos, reloj fijo y un hasher rápido (argon2 es lento a propósito)."""
    with _cliente_sobre(ruta_base, {get_reloj: lambda: reloj, get_hasher: HasherDePrueba}) as c:
        yield c


@pytest.fixture
def sede_id(engine: Engine) -> int:
    with engine.begin() as conn:
        return datos.sede(conn, codigo="CEN", nombre="Sede Central")


@pytest.fixture
def crear_usuario(
    nueva_uow: Callable[[], SqlUnidadDeTrabajo],
) -> Callable[..., Usuario]:
    def crear(username: str, rol: Rol = Rol.ADMIN, sede_id: int | None = None) -> Usuario:
        if rol == Rol.ADMIN:
            return registrar_admin(
                nueva_uow(), HasherDePrueba(), username, username.title(), CONTRASENA
            )
        usuario = Usuario(username, username.title(), f"hash:{CONTRASENA}", rol, sede_id)
        uow = nueva_uow()
        uow.usuarios.agregar(usuario)
        uow.confirmar()
        return usuario

    return crear


def login(cliente: TestClient, username: str, contrasena: str = CONTRASENA) -> dict[str, str]:
    """Inicia sesión y devuelve el header de autorización."""
    respuesta = cliente.post(
        "/api/v1/auth/login", data={"username": username, "password": contrasena}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture
def admin(cliente_limpio: TestClient, crear_usuario: Callable[..., Usuario]) -> dict[str, str]:
    crear_usuario("admin")
    return login(cliente_limpio, "admin")


@pytest.fixture
def bibliotecario(
    cliente_limpio: TestClient, crear_usuario: Callable[..., Usuario], sede_id: int
) -> dict[str, str]:
    crear_usuario("biblio", Rol.BIBLIOTECARIO, sede_id)
    return login(cliente_limpio, "biblio")
