"""API de autenticación: login, usuario actual y formato de errores."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.usuario import Permiso
from tests.controllers.conftest import CLAVE
from tests.factories.datos_orm import crear_admin, crear_sede


def test_login_correcto_devuelve_token_y_usuario_con_permisos(cliente, crear_usuario):
    crear_usuario("ADMIN", username="admin.api")

    r = cliente.post("/api/v1/auth/login", json={"username": "ADMIN.API", "password": CLAVE})

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expires_in"] == 3600
    assert cuerpo["usuario"]["rol"] == "ADMIN"
    assert Permiso.USUARIO_ADMINISTRAR in cuerpo["usuario"]["permisos"]
    assert "password_hash" not in str(cuerpo)


@pytest.mark.ca("CA-ACC-07")
def test_credenciales_invalidas_responden_401_con_el_mismo_mensaje(cliente, crear_usuario):
    crear_usuario("ADMIN", username="admin.api")

    malo_clave = cliente.post("/api/v1/auth/login", json={"username": "admin.api", "password": "x"})
    malo_usuario = cliente.post("/api/v1/auth/login", json={"username": "nadie", "password": CLAVE})

    assert malo_clave.status_code == malo_usuario.status_code == 401
    assert malo_clave.json() == malo_usuario.json()
    assert malo_clave.json()["error"]["codigo"] == "CREDENCIALES_INVALIDAS"


def test_login_sin_campos_responde_422(cliente):
    r = cliente.post("/api/v1/auth/login", json={})

    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "VALIDACION"


def test_me_devuelve_la_sede_del_bibliotecario(cliente, sesion, crear_usuario, autenticar):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin, codigo="NORTE", nombre="Sede Norte")
    biblio = crear_usuario("BIBLIOTECARIO", sede_id=sede.id)

    r = cliente.get("/api/v1/auth/me", headers=autenticar(biblio))

    assert r.status_code == 200
    assert r.json()["sede"] == {"id": sede.id, "codigo": "NORTE", "nombre": "Sede Norte"}
    assert r.json()["permisos"] == [
        "SEDE_LEER_BASICO",
        "SEDE_LEER_PUBLICO",
        "SOCIO_LEER",
        "SOCIO_REGISTRAR",
    ]


@pytest.mark.ca("CA-ACC-11")
def test_sin_token_o_con_token_invalido_responde_401(cliente):
    assert cliente.get("/api/v1/auth/me").status_code == 401
    r = cliente.get("/api/v1/auth/me", headers={"Authorization": "Bearer basura"})

    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "TOKEN_INVALIDO"


@pytest.mark.ca("CA-ACC-11")
def test_un_token_vencido_responde_401(cliente, crear_usuario, autenticar):
    usuario = crear_usuario("ADMIN")
    pasado = datetime.now(UTC) - timedelta(hours=2)

    r = cliente.get("/api/v1/auth/me", headers=autenticar(usuario, ahora=pasado, minutos=60))

    assert r.status_code == 401


@pytest.mark.ca("CA-ACC-12")
def test_un_usuario_dado_de_baja_con_token_vigente_responde_401(
    cliente, sesion, crear_usuario, autenticar
):
    usuario = crear_usuario("ADMIN")
    encabezados = autenticar(usuario)
    assert cliente.get("/api/v1/auth/me", headers=encabezados).status_code == 200

    usuario.activo = False
    sesion.flush()

    assert cliente.get("/api/v1/auth/me", headers=encabezados).status_code == 401


def test_la_documentacion_openapi_de_auth_esta_publicada(cliente):
    rutas = cliente.get("/openapi.json").json()["paths"]

    assert "/api/v1/auth/login" in rutas and "/api/v1/auth/me" in rutas
