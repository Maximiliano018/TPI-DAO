"""Identificador de solicitud (``X-Request-ID``) y registro estructurado de cada solicitud."""

import logging
import re

from app.utils.registro import FiltroDeSolicitud, id_de_solicitud

VERSION = "/api/version"


def test_devuelve_el_identificador_que_manda_el_cliente(cliente):
    r = cliente.get(VERSION, headers={"X-Request-ID": "demo-123"})

    assert r.headers["X-Request-ID"] == "demo-123"


def test_genera_un_identificador_si_no_viene_o_no_es_valido(cliente):
    generado = cliente.get(VERSION).headers["X-Request-ID"]
    invalido = cliente.get(VERSION, headers={"X-Request-ID": "con espacios y\ttabs"})

    assert re.fullmatch(r"[0-9a-f]{32}", generado)
    assert re.fullmatch(r"[0-9a-f]{32}", invalido.headers["X-Request-ID"])
    assert invalido.headers["X-Request-ID"] != generado


def test_cada_solicitud_deja_una_linea_con_su_identificador_y_el_usuario(
    cliente, crear_usuario, autenticar, caplog
):
    admin = crear_usuario("ADMIN")
    caplog.set_level(logging.INFO, logger="app")

    r = cliente.get("/api/v1/auth/me", headers={**autenticar(admin), "X-Request-ID": "traza-42"})

    assert r.status_code == 200
    (linea,) = [x for x in caplog.records if x.name == "app.solicitud"]
    assert linea.request_id == "traza-42"
    assert linea.getMessage().startswith("GET /api/v1/auth/me 200 ")
    assert linea.getMessage().endswith(f"ms usuario={admin.id}")
    assert "Bearer" not in linea.getMessage()


def test_una_solicitud_sin_sesion_se_registra_sin_usuario(cliente, caplog):
    caplog.set_level(logging.INFO, logger="app")

    cliente.get("/api/v1/auth/me")

    (linea,) = [x for x in caplog.records if x.name == "app.solicitud"]
    assert linea.getMessage().startswith("GET /api/v1/auth/me 401 ")
    assert linea.getMessage().endswith("usuario=-")


def test_el_filtro_agrega_el_identificador_vigente_a_cualquier_registro():
    filtro = FiltroDeSolicitud()
    registro = logging.LogRecord("app.servicio", logging.INFO, __file__, 1, "x", None, None)

    filtro.filter(registro)
    assert registro.request_id == "-"  # fuera de una solicitud
    token = id_de_solicitud.set("abc")
    try:
        filtro.filter(registro)
    finally:
        id_de_solicitud.reset(token)
    assert registro.request_id == "abc"
