from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.engine import Engine

from biblioteca.domain.entities.usuario import Usuario
from biblioteca.infrastructure.db import tables as t
from tests.api.conftest import CONTRASENA
from tests.apoyo import RelojFijo

URL_LOGIN = "/api/v1/auth/login"
URL_YO = "/api/v1/auth/yo"


def test_login_devuelve_un_token_y_su_vencimiento(
    cliente_limpio: TestClient, crear_usuario: Callable[..., Usuario]
) -> None:
    crear_usuario("admin")
    respuesta = cliente_limpio.post(URL_LOGIN, data={"username": "ADMIN", "password": CONTRASENA})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["access_token"]
    assert cuerpo["expira_en"].startswith("2026-10-12T23:00")


def test_contrasena_incorrecta_y_usuario_inexistente_responden_igual(
    cliente_limpio: TestClient, crear_usuario: Callable[..., Usuario]
) -> None:
    crear_usuario("admin")
    mala = cliente_limpio.post(URL_LOGIN, data={"username": "admin", "password": "incorrecta"})
    inexistente = cliente_limpio.post(URL_LOGIN, data={"username": "nadie", "password": CONTRASENA})

    assert mala.status_code == inexistente.status_code == 401
    assert mala.json() == inexistente.json()
    assert mala.json()["codigo"] == "CREDENCIALES_INVALIDAS"


def test_yo_devuelve_el_usuario_de_la_sesion(
    cliente_limpio: TestClient, admin: dict[str, str]
) -> None:
    respuesta = cliente_limpio.get(URL_YO, headers=admin)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": respuesta.json()["id"],
        "username": "admin",
        "nombre_completo": "Admin",
        "rol": "ADMIN",
        "sede_id": None,
    }


def test_sin_token_responde_401(cliente_limpio: TestClient) -> None:
    respuesta = cliente_limpio.get(URL_YO)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "NO_AUTENTICADO"
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_el_token_vence(
    cliente_limpio: TestClient, admin: dict[str, str], reloj: RelojFijo
) -> None:
    reloj.adelantar(hours=8, seconds=1)
    assert cliente_limpio.get(URL_YO, headers=admin).status_code == 401


def test_desactivar_al_usuario_invalida_su_token(
    cliente_limpio: TestClient, admin: dict[str, str], engine: Engine
) -> None:
    with engine.begin() as conn:
        conn.execute(update(t.usuario).values(activo=False))

    assert cliente_limpio.get(URL_YO, headers=admin).status_code == 401
    respuesta = cliente_limpio.post(URL_LOGIN, data={"username": "admin", "password": CONTRASENA})
    assert respuesta.status_code == 401
