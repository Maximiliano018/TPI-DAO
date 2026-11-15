"""El administrador tiene los permisos completos: opera en el mostrador de cualquier sede."""

import pytest

from tests.controllers.test_devolucion_api import _devolver
from tests.controllers.test_prestamo_api import (  # noqa: F401
    API,
    _avanzar,
    _prestar,
    _recibir,
    mundo,
)
from tests.controllers.test_sede_api import _error


@pytest.mark.ca("CA-ACC-17")
def test_el_administrador_registra_un_prestamo_indicando_la_sede_de_retiro(cliente, mundo):  # noqa: F811
    _error(_prestar(cliente, mundo["h_admin"], mundo["lucia"], mundo["ej_b"][0]), 422, "VALIDACION")

    r = _prestar(
        cliente,
        mundo["h_admin"],
        mundo["lucia"],
        mundo["ej_b"][0],
        sede_destino_id=mundo["b"]["id"],
    )

    assert r.status_code == 201, r.json()
    assert (r.json()["tipo"], r.json()["registrado_por"]["nombre"]) == ("LOCAL", "Ana Admin")
    entregado = cliente.post(f"{API}/prestamos/{r.json()['id']}/entregar", headers=mundo["h_admin"])
    assert entregado.json()["estado"] == "ACTIVO", entregado.json()
    devuelto = _devolver(cliente, mundo["h_admin"], r.json())
    assert devuelto.json()["prestamo"]["estado"] == "DEVUELTO", devuelto.json()


@pytest.mark.ca("CA-ACC-19")
def test_el_administrador_opera_un_envio_entre_sedes_de_punta_a_punta(cliente, mundo):  # noqa: F811
    ejemplar = mundo["ej_a"][0]
    prestamo = _prestar(
        cliente, mundo["h_admin"], mundo["lucia"], ejemplar, sede_destino_id=mundo["b"]["id"]
    ).json()
    assert prestamo["tipo"] == "INTERBIBLIOTECARIO"
    cuerpo = {
        "sede_destino_id": mundo["b"]["id"],
        "motivo": "ENVIO",
        "lineas": [{"ejemplar_id": ejemplar["id"], "prestamo_id": prestamo["id"]}],
    }
    _error(cliente.post(f"{API}/remitos", json=cuerpo, headers=mundo["h_admin"]), 422, "VALIDACION")
    # El bibliotecario no puede generar un remito desde otra sede.
    _error(
        cliente.post(
            f"{API}/remitos",
            json={**cuerpo, "sede_origen_id": mundo["a"]["id"]},
            headers=mundo["h_b"],
        ),
        403,
        "FORBIDDEN",
    )

    r = cliente.post(
        f"{API}/remitos",
        json={**cuerpo, "sede_origen_id": mundo["a"]["id"]},
        headers=mundo["h_admin"],
    )

    assert r.status_code == 201, r.json()
    remito = _avanzar(cliente, mundo["h_admin"], r.json(), "empaquetar", "despachar")
    recibido = _recibir(cliente, mundo["h_admin"], remito, (ejemplar["id"], "BUENO", {}))
    assert recibido.json()["estado"] == "RECIBIDO", recibido.json()
    entregado = cliente.post(f"{API}/prestamos/{prestamo['id']}/entregar", headers=mundo["h_admin"])
    assert entregado.json()["estado"] == "ACTIVO", entregado.json()
