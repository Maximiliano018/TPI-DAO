from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from biblioteca.api.deps import get_hasher, get_reloj, get_uow
from biblioteca.application.services.usuario_service import UsuarioService
from biblioteca.domain.entities.usuario import Usuario
from biblioteca.domain.enums import Rol
from biblioteca.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from biblioteca.main import app
from tests import datos
from tests.apoyo import HasherDePrueba, RelojFijo

CONTRASENA = "contrasena-segura"


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def cliente(uow: SqlAlchemyUnitOfWork, reloj: RelojFijo) -> Iterator[TestClient]:
    """Cliente HTTP contra la app, con la base, el reloj y el hasher del test."""
    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_reloj] = lambda: reloj
    app.dependency_overrides[get_hasher] = HasherDePrueba
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sede_id(engine: Engine) -> int:
    with engine.begin() as conn:
        return datos.sede(conn, codigo="CEN", nombre="Sede Central")


@pytest.fixture
def crear_usuario(uow: SqlAlchemyUnitOfWork) -> Callable[..., Usuario]:
    def crear(username: str, rol: Rol = Rol.ADMIN, sede_id: int | None = None) -> Usuario:
        if rol == Rol.ADMIN:
            return UsuarioService(uow, HasherDePrueba()).registrar_admin(
                username, username.title(), CONTRASENA
            )
        usuario = Usuario(username, username.title(), f"hash:{CONTRASENA}", rol, sede_id)
        with uow:
            uow.usuarios.agregar(usuario)
            uow.commit()
        return usuario

    return crear


def login(cliente: TestClient, username: str) -> dict[str, str]:
    """Inicia sesión y devuelve el header de autorización."""
    respuesta = cliente.post(
        "/api/v1/auth/login", data={"username": username, "password": CONTRASENA}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture
def admin(cliente: TestClient, crear_usuario: Callable[..., Usuario]) -> dict[str, str]:
    crear_usuario("admin")
    return login(cliente, "admin")


@pytest.fixture
def bibliotecario(
    cliente: TestClient, crear_usuario: Callable[..., Usuario], sede_id: int
) -> dict[str, str]:
    crear_usuario("biblio", Rol.BIBLIOTECARIO, sede_id)
    return login(cliente, "biblio")
