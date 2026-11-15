"""Pago de multas de punta a punta contra PostgreSQL: mostrador y pago en línea simulado."""

from datetime import timedelta

import pytest

from tests.controllers.test_devolucion_api import _devolver, _entregado
from tests.controllers.test_prestamo_api import HOY, mundo  # noqa: F401
from tests.controllers.test_sede_api import _error

API = "/api/v1"


@pytest.fixture
def multa(cliente, mundo, sesion):  # noqa: F811
    """Multa pendiente de Lucía: 5 días de atraso × $200."""
    p = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(5)
    )
    return _devolver(cliente, mundo["h_b"], p).json()["multas"][0]


def _iniciar(cliente, m, multa):
    return cliente.post(f"{API}/multas/{multa['id']}/pagos", headers=m["h_lucia"])


TARJETA = {"forma": "TARJETA_CREDITO", "tarjeta_ultimos4": "3704"}
RECHAZADA = {"forma": "TARJETA_DEBITO", "tarjeta_ultimos4": "0002"}


def _pagar(cliente, m, pago, datos=TARJETA, headers="h_lucia"):
    return cliente.post(f"{API}/pagos/{pago['id']}/pagar", json=datos, headers=m[headers])


def _multa(cliente, m, multa, headers="h_b"):
    items = cliente.get(
        f"{API}/multas", params={"socio_id": m["lucia"]["id"]}, headers=m[headers]
    ).json()["items"]
    return next(x for x in items if x["id"] == multa["id"])


def _socio(cliente, m):
    return cliente.get(f"{API}/socios/{m['lucia']['id']}", headers=m["h_b"]).json()


@pytest.mark.ca("CA-DEV-21")
def test_el_bibliotecario_cobra_en_el_mostrador_con_su_medio(cliente, mundo, multa):  # noqa: F811
    _error(
        cliente.post(
            f"{API}/multas/{multa['id']}/saldar", json={"medio": "EN_LINEA"}, headers=mundo["h_b"]
        ),
        422,
        "VALIDACION",
    )

    r = cliente.post(
        f"{API}/multas/{multa['id']}/saldar",
        json={"medio": "DEBITO", "comprobante": "Cupón 004512"},
        headers=mundo["h_b"],
    )

    assert r.status_code == 200, r.json()
    assert (r.json()["estado"], r.json()["pago"]["medio"]) == ("SALDADA", "DEBITO")
    assert r.json()["pago"]["comprobante"] == "Cupón 004512"
    assert r.json()["pago"]["registrado_por"]["nombre"] == "Beto B"
    propia = _multa(cliente, mundo, multa, "h_lucia")
    assert propia["pago"]["medio"] == "DEBITO"
    assert "comprobante" not in propia["pago"] and "registrado_por" not in propia["pago"]
    assert _socio(cliente, mundo)["estado"] == "HABILITADO"


@pytest.mark.ca("CA-DEV-22")
def test_el_socio_inicia_el_pago_en_linea_y_lo_retoma(cliente, mundo, multa):  # noqa: F811
    r = _iniciar(cliente, mundo, multa)

    assert r.status_code == 201, r.json()
    pago = r.json()
    assert (pago["estado"], pago["medio"], pago["monto"]) == ("PENDIENTE", "EN_LINEA", "1000.00")
    assert _iniciar(cliente, mundo, multa).json()["id"] == pago["id"]
    assert _multa(cliente, mundo, multa, "h_lucia")["pago_en_curso"]["id"] == pago["id"]
    detalle = cliente.get(f"{API}/pagos/{pago['id']}", headers=mundo["h_lucia"]).json()
    assert detalle["estado"] == "PENDIENTE"


@pytest.mark.ca("CA-DEV-23")
def test_al_aprobar_el_pago_simulado_la_multa_queda_saldada(cliente, mundo, multa):  # noqa: F811
    pago = _iniciar(cliente, mundo, multa).json()

    r = _pagar(cliente, mundo, pago)

    assert r.status_code == 200, r.json()
    assert (r.json()["estado"], r.json()["forma_en_linea"], r.json()["tarjeta_ultimos4"]) == (
        "APROBADO",
        "TARJETA_CREDITO",
        "3704",
    )
    assert r.json()["numero_comprobante"].startswith("PG-")
    saldada = _multa(cliente, mundo, multa)
    assert (saldada["estado"], saldada["pago"]["id"], saldada["pago"]["medio"]) == (
        "SALDADA",
        pago["id"],
        "EN_LINEA",
    )
    assert saldada["saldada_por"] is None  # la saldó el pago en línea, no una persona
    assert _socio(cliente, mundo)["estado"] == "HABILITADO"
    _error(_pagar(cliente, mundo, pago), 409, "TRANSICION_INVALIDA")


@pytest.mark.ca("CA-DEV-24")
def test_un_pago_rechazado_deja_la_multa_pendiente_y_se_reintenta(cliente, mundo, multa):  # noqa: F811
    primero = _iniciar(cliente, mundo, multa).json()

    rechazado = _pagar(cliente, mundo, primero, RECHAZADA).json()

    assert (rechazado["estado"], rechazado["motivo"]) == (
        "RECHAZADO",
        "Tarjeta rechazada por el emisor (tarjeta de prueba)",
    )
    assert _multa(cliente, mundo, multa)["estado"] == "PENDIENTE"
    segundo = _iniciar(cliente, mundo, multa).json()
    assert segundo["id"] != primero["id"] and segundo["estado"] == "PENDIENTE"


@pytest.mark.ca("CA-DEV-25")
def test_cobrar_en_el_mostrador_cancela_el_pago_en_linea_en_curso(cliente, mundo, multa):  # noqa: F811
    pago = _iniciar(cliente, mundo, multa).json()

    cliente.post(
        f"{API}/multas/{multa['id']}/saldar", json={"medio": "EFECTIVO"}, headers=mundo["h_b"]
    )

    cancelado = cliente.get(f"{API}/pagos/{pago['id']}", headers=mundo["h_b"]).json()
    assert (cancelado["estado"], cancelado["motivo"]) == ("CANCELADO", "Se cobró en el mostrador")
    _error(_pagar(cliente, mundo, pago), 409, "TRANSICION_INVALIDA")
    assert _multa(cliente, mundo, multa)["pago"]["medio"] == "EFECTIVO"


@pytest.mark.ca("CA-DEV-26")
def test_solo_el_socio_paga_en_linea_y_solo_sus_multas(cliente, mundo, multa):  # noqa: F811
    _error(
        cliente.post(f"{API}/multas/{multa['id']}/pagos", headers=mundo["h_b"]), 403, "FORBIDDEN"
    )
    _error(
        cliente.post(f"{API}/multas/999999/pagos", headers=mundo["h_lucia"]),
        404,
        "MULTA_NO_ENCONTRADA",
    )
    pago = _iniciar(cliente, mundo, multa).json()
    _error(_pagar(cliente, mundo, pago, headers="h_b"), 403, "FORBIDDEN")
    assert _multa(cliente, mundo, multa)["estado"] == "PENDIENTE"


@pytest.mark.ca("CA-DEV-28")
def test_de_la_tarjeta_solo_se_aceptan_los_ultimos_4_digitos(cliente, mundo, multa):  # noqa: F811
    pago = _iniciar(cliente, mundo, multa).json()
    completa = {"forma": "TARJETA_CREDITO", "tarjeta_ultimos4": "4509953566233704"}

    _error(_pagar(cliente, mundo, pago, completa), 422, "VALIDACION")
    _error(_pagar(cliente, mundo, pago, {"forma": "TARJETA_CREDITO"}), 422, "VALIDACION")
    r = _pagar(cliente, mundo, pago, {"forma": "DINERO_EN_CUENTA"})

    assert (r.json()["estado"], r.json()["tarjeta_ultimos4"]) == ("APROBADO", None)


@pytest.mark.ca("CA-DEV-27")
def test_el_pago_aprobado_tiene_su_comprobante_en_pdf(cliente, mundo, multa):  # noqa: F811
    pago = _iniciar(cliente, mundo, multa).json()
    url = f"{API}/pagos/{pago['id']}/comprobante"
    _error(cliente.get(url, headers=mundo["h_lucia"]), 409, "TRANSICION_INVALIDA")

    aprobado = _pagar(cliente, mundo, pago).json()
    propio = cliente.get(url, headers=mundo["h_lucia"])
    personal = cliente.get(url, headers=mundo["h_b"])

    assert propio.status_code == 200
    assert propio.headers["content-type"] == "application/pdf"
    nombre = f"comprobante-{aprobado['numero_comprobante']}.pdf"
    assert propio.headers["content-disposition"] == f'attachment; filename="{nombre}"'
    assert propio.content.startswith(b"%PDF-")
    assert aprobado["numero_comprobante"].encode() in propio.content
    assert personal.status_code == 200


@pytest.mark.ca("CA-DEV-27")
def test_el_cobro_del_mostrador_tambien_tiene_comprobante(cliente, mundo, multa):  # noqa: F811
    saldada = cliente.post(
        f"{API}/multas/{multa['id']}/saldar",
        json={"medio": "EFECTIVO", "comprobante": "Recibo 77"},
        headers=mundo["h_b"],
    ).json()

    r = cliente.get(f"{API}/pagos/{saldada['pago']['id']}/comprobante", headers=mundo["h_lucia"])

    assert r.status_code == 200
    assert "Cobrado por".encode("cp1252") in r.content
    assert b"Recibo 77" in r.content
