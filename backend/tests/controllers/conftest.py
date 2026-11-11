"""Cliente HTTP contra la API con la base de pruebas (transacción por prueba)."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.config.security import crear_token, hashear_clave
from app.db.models import UsuarioORM
from app.db.session import sesion_por_solicitud
from app.main import app

CLAVE = "Clave-de-prueba-1"


@pytest.fixture
def cliente(sesion: Session) -> Iterator[TestClient]:
    """TestClient cuyas solicitudes usan la sesión transaccional de la prueba."""
    app.dependency_overrides[sesion_por_solicitud] = lambda: sesion
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def crear_usuario(sesion: Session) -> Callable[..., UsuarioORM]:
    """Crea usuarios ORM con la contraseña de prueba."""
    contador = {"n": 0}
    hash_comun = hashear_clave(CLAVE)

    def _crear(rol: str = "ADMIN", **over) -> UsuarioORM:
        contador["n"] += 1
        datos = {
            "username": f"u{contador['n']}.{rol.lower()}",
            "password_hash": hash_comun,
            "nombre": f"Usuario {contador['n']}",
            "rol": rol,
            "activo": True,
        }
        datos.update(over)
        usuario = UsuarioORM(**datos)
        sesion.add(usuario)
        sesion.flush()
        return usuario

    return _crear


@pytest.fixture
def autenticar() -> Callable[..., dict[str, str]]:
    """Devuelve encabezados con un token real firmado con la clave de prueba."""

    def _encabezados(usuario: UsuarioORM, ahora=None, minutos: int = 60) -> dict[str, str]:
        token = crear_token(
            usuario_id=usuario.id,
            rol=usuario.rol,
            sede_id=usuario.sede_id,
            ahora=ahora or datetime.now(UTC),
            minutos=minutos,
            clave=get_settings().secret_key,
        )
        return {"Authorization": f"Bearer {token}"}

    return _encabezados
