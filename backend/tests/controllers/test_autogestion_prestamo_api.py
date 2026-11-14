"""Autogestión de préstamos: el socio pide un libro para sí y el sistema elige tipo y ejemplar.

Usa el mundo de ``test_prestamo_api``: Lucía es socia de la sede B (su sede de alta) y tiene
cuenta; Juan es socio sin cuenta. Los libros 0 y 1 tienen ejemplares en A y en B; los libros 2 a
4, solo en A.
"""

from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.controllers.test_prestamo_api import (
    API,
    _avanzar,
    _prestar,
    _recibir,
    _remito,
    mundo,  # noqa: F401  (fixture compartido)
)
from tests.controllers.test_sede_api import _error
from tests.fakes.reloj import HOY_DE_PRUEBAS

PROPUESTA = f"{API}/prestamos/solicitudes/propuesta"
SOLICITUDES = f"{API}/prestamos/solicitudes"


def _ejemplar(cliente, m, libro, sede, codigo):
    r = cliente.post(
        f"{API}/ejemplares",
        json={"libro_id": libro["id"], "codigo_inventario": codigo, "sede_id": sede["id"]},
        headers=m["h_admin"],
    )
    assert r.status_code == 201, r.json()
    return r.json()


def _libro_sin_ejemplares(cliente, m):
    r = cliente.post(
        f"{API}/libros",
        json={"titulo": "Sin copias", "autores": ["Nadie"], "categoria_id": 1},
        headers=m["h_admin"],
    )
    return r.json()


def _solicitar(cliente, m, libro, **over):
    return cliente.post(SOLICITUDES, json={"libro_id": libro["id"], **over}, headers=m["h_lucia"])


def _proponer(cliente, m, libro, **params):
    return cliente.get(PROPUESTA, params={"libro_id": libro["id"], **params}, headers=m["h_lucia"])


# --- tipo y ejemplar los elige el sistema ----------------------------------------------------


@pytest.mark.ca("CA-PRE-19", "CA-PRE-24")
def test_con_disponibles_en_su_sede_el_prestamo_es_local_y_tiene_plazo_de_retiro(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][0]
    limite = (HOY_DE_PRUEBAS + timedelta(days=3)).isoformat()

    propuesta = _proponer(cliente, mundo, libro).json()
    assert (propuesta["tipo"], propuesta["sede_destino"]["id"]) == ("LOCAL", mundo["b"]["id"])
    assert (propuesta["sede_origen"]["id"], propuesta["retiro_hasta"]) == (mundo["b"]["id"], limite)
    assert propuesta["plazo_dias"] == 14

    r = _solicitar(cliente, mundo, libro, sede_origen_esperada_id=mundo["b"]["id"])

    assert r.status_code == 201, r.json()
    prestamo = r.json()
    assert (prestamo["tipo"], prestamo["estado"], prestamo["socio_id"]) == (
        "LOCAL",
        "SOLICITADO",
        mundo["lucia"]["id"],
    )
    assert (prestamo["codigo_ejemplar"], prestamo["fecha_limite_retiro"]) == ("B-0", limite)
    assert "registrado_por" not in prestamo
    detalle = cliente.get(f"{API}/prestamos/{prestamo['id']}", headers=mundo["h_lucia"]).json()
    assert detalle["historial"][0]["autor"] == "Vos"


@pytest.mark.ca("CA-PRE-20")
def test_sin_disponibles_en_destino_sale_de_la_sede_con_mas_disponibles(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][3]  # 1 en A
    _ejemplar(cliente, mundo, libro, mundo["c"], "C-3A")
    _ejemplar(cliente, mundo, libro, mundo["c"], "C-3B")

    r = _solicitar(cliente, mundo, libro)

    assert r.status_code == 201, r.json()
    assert (r.json()["tipo"], r.json()["sede_origen_id"], r.json()["sede_destino_id"]) == (
        "INTERBIBLIOTECARIO",
        mundo["c"]["id"],
        mundo["b"]["id"],
    )
    assert r.json()["fecha_limite_retiro"] is None  # empieza cuando llega a B


@pytest.mark.ca("CA-PRE-21")
def test_con_empate_sale_de_la_sede_de_menor_id(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][4]  # 1 en A
    _ejemplar(cliente, mundo, libro, mundo["c"], "C-4")
    assert mundo["a"]["id"] < mundo["c"]["id"]

    assert _proponer(cliente, mundo, libro).json()["sede_origen"]["id"] == mundo["a"]["id"]


@pytest.mark.ca("CA-PRE-24")
def test_el_socio_puede_elegir_otra_sede_de_retiro(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][2]  # solo en A

    r = _solicitar(cliente, mundo, libro, sede_destino_id=mundo["a"]["id"])

    assert (r.json()["tipo"], r.json()["sede_destino_id"]) == ("LOCAL", mundo["a"]["id"])


@pytest.mark.ca("CA-PRE-22")
def test_sin_disponibles_en_la_red_se_rechaza_y_no_se_crea_nada(cliente, mundo, sesion):  # noqa: F811
    libro = _libro_sin_ejemplares(cliente, mundo)
    antes = sesion.scalar(text("SELECT count(*) FROM prestamo"))

    _error(_proponer(cliente, mundo, libro), 409, "SIN_EJEMPLARES_DISPONIBLES")
    error = _error(_solicitar(cliente, mundo, libro), 409, "SIN_EJEMPLARES_DISPONIBLES")

    assert error["detalles"][0]["sede_destino_id"] == mundo["b"]["id"]  # para ofrecer reservar
    assert sesion.scalar(text("SELECT count(*) FROM prestamo")) == antes


@pytest.mark.ca("CA-PRE-23")
def test_un_socio_inhabilitado_se_rechaza_antes_de_buscar_ejemplares(cliente, mundo):  # noqa: F811
    cliente.post(
        f"{API}/socios/{mundo['lucia']['id']}/inhabilitar",
        json={"motivo": "Daño reiterado de material"},
        headers=mundo["h_admin"],
    )
    libro = _libro_sin_ejemplares(cliente, mundo)

    _error(_solicitar(cliente, mundo, libro), 409, "SOCIO_INHABILITADO")


@pytest.mark.ca("CA-PRE-28")
def test_si_la_disponibilidad_cambio_se_pide_confirmar_la_nueva_propuesta(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][4]  # 1 en A
    _ejemplar(cliente, mundo, libro, mundo["c"], "C-4")
    propuesta = _proponer(cliente, mundo, libro).json()
    assert propuesta["sede_origen"]["id"] == mundo["a"]["id"]
    # Mientras tanto, la sede A presta su ejemplar en mostrador.
    assert _prestar(cliente, mundo["h_a"], mundo["juan"], mundo["ej_a"][4]).status_code == 201

    error = _error(
        _solicitar(cliente, mundo, libro, sede_origen_esperada_id=mundo["a"]["id"]),
        409,
        "DISPONIBILIDAD_CAMBIADA",
    )

    assert error["detalles"][0]["sede_origen_id"] == mundo["c"]["id"]


# --- el socio solo pide para sí ---------------------------------------------------------------


@pytest.mark.ca("CA-ACC-15")
def test_un_socio_no_pide_prestamos_a_nombre_de_otro(cliente, mundo, sesion):  # noqa: F811
    libro = mundo["libros"][0]

    _error(_solicitar(cliente, mundo, libro, socio_id=mundo["juan"]["id"]), 403, "FORBIDDEN")
    _error(_proponer(cliente, mundo, libro, socio_id=mundo["juan"]["id"]), 403, "FORBIDDEN")
    # Tampoco puede usar el registro de mostrador, ni para sí ni para otro.
    _error(_prestar(cliente, mundo["h_lucia"], mundo["juan"], mundo["ej_b"][0]), 403, "FORBIDDEN")
    _error(_prestar(cliente, mundo["h_lucia"], mundo["lucia"], mundo["ej_b"][0]), 403, "FORBIDDEN")
    assert sesion.scalar(text("SELECT count(*) FROM prestamo")) == 0


@pytest.mark.ca("CA-ACC-16", "CA-ACC-17")
def test_el_personal_no_usa_la_autogestion_y_el_administrador_no_registra(cliente, mundo):  # noqa: F811
    cuerpo = {"libro_id": mundo["libros"][0]["id"], "socio_id": mundo["lucia"]["id"]}
    for headers in (mundo["h_b"], mundo["h_admin"]):
        _error(cliente.post(SOLICITUDES, json=cuerpo, headers=headers), 403, "FORBIDDEN")
    _error(_prestar(cliente, mundo["h_admin"], mundo["lucia"], mundo["ej_b"][0]), 403, "FORBIDDEN")


# --- cancelación y plazo de retiro ------------------------------------------------------------


@pytest.mark.ca("CA-PRE-27")
def test_el_socio_cancela_su_solicitud_pero_no_la_ajena_ni_una_en_camino(cliente, mundo):  # noqa: F811
    propio = _solicitar(cliente, mundo, mundo["libros"][0]).json()
    ajeno = _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][1]).json()

    r = cliente.post(f"{API}/prestamos/{propio['id']}/cancelar", json={}, headers=mundo["h_lucia"])
    assert r.json()["estado"] == "CANCELADO"
    ejemplar = cliente.get(f"{API}/ejemplares/{propio['ejemplar_id']}", headers=mundo["h_b"])
    assert ejemplar.json()["estado"] == "DISPONIBLE"
    _error(
        cliente.post(f"{API}/prestamos/{ajeno['id']}/cancelar", json={}, headers=mundo["h_lucia"]),
        404,
        "PRESTAMO_NO_ENCONTRADO",
    )

    entre_sedes = _solicitar(cliente, mundo, mundo["libros"][2]).json()  # sale de A
    ida = _remito(
        cliente,
        mundo["h_a"],
        mundo["b"],
        [{"ejemplar_id": entre_sedes["ejemplar_id"], "prestamo_id": entre_sedes["id"]}],
    )
    assert ida.status_code == 201, ida.json()
    _error(
        cliente.post(
            f"{API}/prestamos/{entre_sedes['id']}/cancelar", json={}, headers=mundo["h_lucia"]
        ),
        409,
        "TRANSICION_INVALIDA",
    )


def _vencer_retiro(cliente, m, sesion, prestamo_id):
    sesion.execute(
        text("UPDATE prestamo SET fecha_limite_retiro = current_date - 1 WHERE id = :id"),
        {"id": prestamo_id},
    )
    r = cliente.post(f"{API}/admin/tareas/vencer-retiros", headers=m["h_admin"])
    assert r.status_code == 200, r.json()
    return r.json()["cambios"]


@pytest.mark.ca("CA-PRE-25")
def test_un_local_no_retirado_a_tiempo_se_cancela_y_libera_el_ejemplar(cliente, mundo, sesion):  # noqa: F811
    prestamo = _solicitar(cliente, mundo, mundo["libros"][0]).json()

    assert _vencer_retiro(cliente, mundo, sesion, prestamo["id"]) == 1

    detalle = cliente.get(f"{API}/prestamos/{prestamo['id']}", headers=mundo["h_lucia"]).json()
    assert detalle["estado"] == "CANCELADO"
    assert detalle["historial"][-1]["autor"] == "Sistema"
    assert detalle["historial"][-1]["observacion"].startswith("No se retiró a tiempo")
    ejemplar = cliente.get(f"{API}/ejemplares/{prestamo['ejemplar_id']}", headers=mundo["h_b"])
    assert ejemplar.json()["estado"] == "DISPONIBLE"


@pytest.mark.ca("CA-PRE-26")
def test_un_interbibliotecario_que_llego_y_no_se_retiro_vuelve_a_su_sede(cliente, mundo, sesion):  # noqa: F811
    prestamo = _solicitar(cliente, mundo, mundo["libros"][2]).json()  # de A a B
    ida = _remito(
        cliente,
        mundo["h_a"],
        mundo["b"],
        [{"ejemplar_id": prestamo["ejemplar_id"], "prestamo_id": prestamo["id"]}],
    ).json()
    _avanzar(cliente, mundo["h_a"], ida, "empaquetar", "despachar")
    _recibir(cliente, mundo["h_b"], ida, (prestamo["ejemplar_id"], "BUENO", {}))
    llegado = cliente.get(f"{API}/prestamos/{prestamo['id']}", headers=mundo["h_lucia"]).json()
    limite = (HOY_DE_PRUEBAS + timedelta(days=3)).isoformat()
    assert (llegado["estado"], llegado["fecha_limite_retiro"]) == ("EN_ENVIO", limite)
    assert llegado["historial"][-1]["observacion"].startswith("Disponible para retirar hasta")

    assert _vencer_retiro(cliente, mundo, sesion, prestamo["id"]) == 1

    detalle = cliente.get(f"{API}/prestamos/{prestamo['id']}", headers=mundo["h_b"]).json()
    assert detalle["estado"] == "CANCELADO"
    assert [(r["motivo"], r["estado"]) for r in detalle["remitos"]] == [
        ("ENVIO", "RECIBIDO"),
        ("RETORNO", "GENERADO"),
    ]


# --- lo que ve el socio de sus préstamos (P1) -------------------------------------------------


@pytest.mark.ca("CA-PRE-29")
def test_el_socio_no_ve_la_identidad_del_personal(cliente, mundo):  # noqa: F811
    prestamo = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    ruta = f"{API}/prestamos/{prestamo['id']}"

    socio = cliente.get(ruta, headers=mundo["h_lucia"]).json()
    assert "registrado_por" not in socio
    assert [(m["autor"], m["usuario"]) for m in socio["historial"]] == [
        ("Personal de la biblioteca", None)
    ]
    listado = cliente.get(f"{API}/prestamos", headers=mundo["h_lucia"]).json()["items"]
    assert "registrado_por" not in listado[0]

    personal = cliente.get(ruta, headers=mundo["h_b"]).json()
    assert personal["registrado_por"]["nombre"] == "Beto B"
    assert personal["historial"][0]["autor"] == "Beto B"
    assert personal["historial"][0]["usuario"]["nombre"] == "Beto B"
