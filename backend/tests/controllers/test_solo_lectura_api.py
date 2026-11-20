"""Usuarios de solo lectura (``USUARIOS_SOLO_LECTURA``): ven todo, pero no modifican nada."""

from collections.abc import Iterable, Iterator

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from app.config import Settings, get_settings
from app.controllers.dependencies import usuario_actual
from app.main import app
from tests.controllers.conftest import CLAVE

METODOS_DE_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}
# Lo único que se puede pedir sin sesión y no es una lectura.
PUBLICAS_DE_ESCRITURA = {"POST /api/v1/auth/login"}


@pytest.fixture
def con_visitante(cliente):
    """Configura ``visitante`` como usuario de solo lectura durante la prueba."""
    ajustes = get_settings().model_copy(update={"usuarios_solo_lectura": "visitante"})
    app.dependency_overrides[get_settings] = lambda: ajustes
    return cliente


def test_la_variable_admite_varios_usuarios_sin_distinguir_mayusculas():
    ajustes = Settings(usuarios_solo_lectura=" Visitante , visitante.socio,")

    assert ajustes.es_solo_lectura("visitante")
    assert ajustes.es_solo_lectura("VISITANTE.SOCIO")
    assert not ajustes.es_solo_lectura("admin")
    assert not Settings(usuarios_solo_lectura="").es_solo_lectura("visitante")


def test_el_visitante_puede_consultar(con_visitante, crear_usuario, autenticar):
    visitante = crear_usuario("ADMIN", username="visitante")
    encabezados = autenticar(visitante)

    for ruta in ("/api/v1/sedes", "/api/v1/socios", "/api/v1/prestamos", "/api/v1/parametros"):
        assert con_visitante.get(ruta, headers=encabezados).status_code == 200, ruta


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("POST", "/api/v1/sedes"),
        ("PUT", "/api/v1/sedes/1"),
        ("POST", "/api/v1/sedes/1/baja"),
        ("DELETE", "/api/v1/sedes/1/excepciones-horario/1"),
        ("POST", "/api/v1/usuarios/1/baja"),
        ("PUT", "/api/v1/parametros/MULTA_POR_DIA"),
        ("POST", "/api/v1/prestamos"),
    ],
)
def test_el_visitante_no_puede_modificar_nada(
    con_visitante, crear_usuario, autenticar, metodo, ruta
):
    visitante = crear_usuario("ADMIN", username="visitante")

    r = con_visitante.request(metodo, ruta, json={}, headers=autenticar(visitante))

    assert r.status_code == 403
    assert r.json()["error"]["codigo"] == "SOLO_LECTURA"
    assert "solo lectura" in r.json()["error"]["mensaje"]


def test_login_y_me_avisan_que_es_de_solo_lectura(con_visitante, crear_usuario, autenticar):
    crear_usuario("ADMIN", username="visitante")
    admin = crear_usuario("ADMIN", username="admin.real")

    login = con_visitante.post(
        "/api/v1/auth/login", json={"username": "visitante", "password": CLAVE}
    )
    token = login.json()["access_token"]
    me = con_visitante.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    me_admin = con_visitante.get("/api/v1/auth/me", headers=autenticar(admin))

    assert login.status_code == 200
    assert login.json()["usuario"]["solo_lectura"] is True
    assert me.json()["solo_lectura"] is True
    assert me_admin.json()["solo_lectura"] is False


def test_sin_la_variable_nadie_es_de_solo_lectura(cliente, crear_usuario, autenticar):
    visitante = crear_usuario("ADMIN", username="visitante")
    encabezados = autenticar(visitante)

    assert cliente.get("/api/v1/auth/me", headers=encabezados).json()["solo_lectura"] is False
    r = cliente.post("/api/v1/sedes", json={}, headers=encabezados)
    assert r.json()["error"]["codigo"] == "VALIDACION"


def _rutas(rutas: Iterable[BaseRoute]) -> Iterator[APIRoute]:
    """Las rutas de la API, también las de los routers incluidos (FastAPI los anida)."""
    for ruta in rutas:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif (router := getattr(ruta, "original_router", None)) is not None:
            yield from _rutas(router.routes)


def _depende_de(dependant: Dependant, llamada) -> bool:
    return any(d.call is llamada or _depende_de(d, llamada) for d in dependant.dependencies)


def test_toda_ruta_que_modifica_pasa_por_el_control_de_solo_lectura():
    """El control vive en ``usuario_actual``: ninguna escritura puede saltearlo."""
    sin_control = [
        f"{metodo} {ruta.path_format}"
        for ruta in _rutas(app.routes)
        for metodo in ruta.methods & METODOS_DE_ESCRITURA
        if f"{metodo} {ruta.path_format}" not in PUBLICAS_DE_ESCRITURA
        and not _depende_de(ruta.dependant, usuario_actual)
    ]

    assert sin_control == []
