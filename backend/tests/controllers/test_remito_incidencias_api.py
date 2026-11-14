"""Remitos: responsable de las incidencias, ejemplares faltantes, plazo de despacho y
recuperación de un ejemplar extraviado.

Usa el mundo de ``test_prestamo_api``: Lucía y Juan son socios de la sede B; los libros 0 y 1
tienen ejemplares en A y en B, y los libros 2 a 4 solo en A.
"""

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


def _envio(cliente, m, *pares):
    """Préstamos de A hacia B para cada (socio, ejemplar) y el remito que los lleva, despachado."""
    prestamos = [_prestar(cliente, m["h_b"], socio, ej).json() for socio, ej in pares]
    remito = _remito(
        cliente,
        m["h_a"],
        m["b"],
        [{"ejemplar_id": p["ejemplar_id"], "prestamo_id": p["id"]} for p in prestamos],
    ).json()
    _avanzar(cliente, m["h_a"], remito, "empaquetar", "despachar")
    return remito, prestamos


def _detalle(cliente, m, remito):
    return cliente.get(f"{API}/remitos/{remito['id']}", headers=m["h_admin"]).json()


def _ejemplar(cliente, m, ejemplar_id):
    return cliente.get(f"{API}/ejemplares/{ejemplar_id}", headers=m["h_admin"]).json()


# --- R1. responsable de las incidencias -------------------------------------------------------


@pytest.mark.ca("CA-REM-22")
def test_la_incidencia_de_un_envio_es_de_la_sede_origen_y_no_del_socio(cliente, mundo, sesion):  # noqa: F811
    remito, _ = _envio(cliente, mundo, (mundo["juan"], mundo["ej_a"][1]))

    _recibir(
        cliente,
        mundo["h_b"],
        remito,
        (mundo["ej_a"][1]["id"], "DANADO", {"observacion": "Mojado en el viaje"}),
    )

    [incidencia] = _detalle(cliente, mundo, remito)["incidencias"]
    assert (incidencia["tipo"], incidencia["origen"]) == ("DANIO", "REMITO")
    assert incidencia["sede_responsable"] == {"id": mundo["a"]["id"], "nombre": "Sede SEDE_A"}
    assert incidencia["despachado_por"]["nombre"] == "Bea A"
    assert incidencia["usuario"]["nombre"] == "Beto B"  # quien la registró al recibir
    assert sesion.scalar(text("SELECT count(*) FROM incidencia WHERE socio_id IS NOT NULL")) == 0


@pytest.mark.ca("CA-REM-22")
def test_un_extravio_en_transito_tampoco_se_asocia_al_socio(cliente, mundo, sesion):  # noqa: F811
    remito, _ = _envio(cliente, mundo, (mundo["lucia"], mundo["ej_a"][0]))
    sesion.execute(
        text("UPDATE remito SET fecha_despacho = now() - interval '8 days' WHERE id = :id"),
        {"id": remito["id"]},
    )
    sesion.commit()

    cliente.post(
        f"{API}/remitos/{remito['id']}/extraviado",
        json={"motivo": "No llegó a destino"},
        headers=mundo["h_admin"],
    )

    [incidencia] = _detalle(cliente, mundo, remito)["incidencias"]
    assert (incidencia["tipo"], incidencia["sede_responsable"]["id"]) == (
        "EXTRAVIO",
        mundo["a"]["id"],
    )
    assert sesion.scalar(text("SELECT socio_id FROM incidencia")) is None


@pytest.mark.ca("CA-REM-22")
def test_la_incidencia_de_una_devolucion_sigue_a_cargo_del_socio(cliente, mundo, sesion):  # noqa: F811
    prestamo = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    cliente.post(f"{API}/prestamos/{prestamo['id']}/entregar", headers=mundo["h_b"])

    cliente.post(
        f"{API}/prestamos/{prestamo['id']}/devolucion",
        json={"estado_fisico": "EXTRAVIADO", "observaciones": "Lo perdió en el colectivo"},
        headers=mundo["h_b"],
    )

    fila = sesion.execute(
        text("SELECT origen, socio_id, sede_responsable_id FROM incidencia")
    ).one()
    assert tuple(fila) == ("DEVOLUCION", mundo["lucia"]["id"], None)


# --- R2. ejemplares faltantes -----------------------------------------------------------------


@pytest.mark.ca("CA-REM-23")
def test_un_ejemplar_faltante_se_da_de_baja_y_el_resto_se_recibe(cliente, mundo):  # noqa: F811
    llega, falta = mundo["ej_a"][0], mundo["ej_a"][1]
    remito, (p_llega, p_falta) = _envio(
        cliente, mundo, (mundo["lucia"], llega), (mundo["juan"], falta)
    )

    r = _recibir(
        cliente,
        mundo["h_b"],
        remito,
        (llega["id"], "BUENO", {}),
        (falta["id"], None, {"faltante": True, "observacion": "No venía en la caja"}),
    )

    assert r.status_code == 200, r.json()
    assert r.json()["estado"] == "INCOMPLETO"
    lineas = {linea["ejemplar_id"]: linea for linea in r.json()["lineas"]}
    assert (lineas[falta["id"]]["resultado"], lineas[falta["id"]]["estado_fisico_llegada"]) == (
        "FALTANTE",
        None,
    )
    faltante = _ejemplar(cliente, mundo, falta["id"])
    assert (faltante["estado"], faltante["motivo_baja"]) == (
        "BAJA",
        f"Faltante en el remito {remito['numero']}",
    )
    assert (faltante["sede_actual_id"], faltante["recuperable"]) == (mundo["a"]["id"], True)
    assert _ejemplar(cliente, mundo, llega["id"])["estado"] == "APARTADO"
    estados = {
        p["id"]: cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()["estado"]
        for p in (p_llega, p_falta)
    }
    assert estados == {p_llega["id"]: "EN_ENVIO", p_falta["id"]: "CANCELADO"}
    [incidencia] = r.json()["incidencias"]
    assert (incidencia["tipo"], incidencia["sede_responsable"]["id"]) == (
        "EXTRAVIO",
        mundo["a"]["id"],
    )


@pytest.mark.ca("CA-REM-24")
def test_si_no_llego_ningun_ejemplar_el_remito_sigue_en_transito(cliente, mundo):  # noqa: F811
    ej = mundo["ej_a"][0]
    remito, _ = _envio(cliente, mundo, (mundo["lucia"], ej))

    _error(
        _recibir(
            cliente,
            mundo["h_b"],
            remito,
            (ej["id"], None, {"faltante": True, "observacion": "Caja vacía"}),
        ),
        422,
        "REMITO_INVALIDO",
    )
    _error(
        _recibir(cliente, mundo["h_b"], remito, (ej["id"], None, {})), 422, "REMITO_INVALIDO"
    )  # un ejemplar que llegó necesita su estado físico
    assert _detalle(cliente, mundo, remito)["estado"] == "DESPACHADO"  # no cambió nada


# --- R3. plazo de despacho --------------------------------------------------------------------


@pytest.mark.ca("CA-REM-25")
def test_un_remito_sin_despachar_pasado_el_plazo_figura_atrasado(cliente, mundo, sesion):  # noqa: F811
    viejo = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": mundo["ej_a"][0]["id"]}], "TRASLADO"
    ).json()
    nuevo = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": mundo["ej_a"][1]["id"]}], "TRASLADO"
    ).json()
    assert (nuevo["atrasado"], nuevo["despachar_hasta"] is not None) == (False, True)
    sesion.execute(
        text("UPDATE remito SET fecha_generacion = now() - interval '5 days' WHERE id = :id"),
        {"id": viejo["id"]},
    )
    sesion.commit()

    assert _detalle(cliente, mundo, viejo)["atrasado"] is True
    atrasados = cliente.get(
        f"{API}/remitos", params={"atrasados": True}, headers=mundo["h_a"]
    ).json()["items"]
    assert [r["numero"] for r in atrasados] == [viejo["numero"]]
    # Al despacharlo deja de estar atrasado (ya salió).
    despachado = _avanzar(cliente, mundo["h_a"], viejo, "empaquetar", "despachar")
    assert (despachado["atrasado"], despachado["despachar_hasta"]) == (False, None)


# --- R4. recuperar un ejemplar extraviado -----------------------------------------------------


def _faltante(cliente, m):
    llega, falta = m["ej_a"][0], m["ej_a"][1]
    remito, _ = _envio(cliente, m, (m["lucia"], llega), (m["juan"], falta))
    _recibir(
        cliente,
        m["h_b"],
        remito,
        (llega["id"], "BUENO", {}),
        (falta["id"], None, {"faltante": True, "observacion": "No venía en la caja"}),
    )
    return remito, falta


@pytest.mark.ca("CA-CAT-20")
def test_la_sede_propietaria_recupera_un_ejemplar_extraviado_que_aparecio(cliente, mundo):  # noqa: F811
    remito, falta = _faltante(cliente, mundo)
    ejemplar = _ejemplar(cliente, mundo, falta["id"])
    ruta = f"{API}/ejemplares/{falta['id']}/recuperar"
    cuerpo = {
        "estado_fisico": "REGULAR",
        "observacion": "Apareció en el depósito",
        "version": ejemplar["version"],
    }

    _error(cliente.post(ruta, json=cuerpo, headers=mundo["h_b"]), 403, "FORBIDDEN")
    r = cliente.post(ruta, json=cuerpo, headers=mundo["h_a"])

    assert r.status_code == 200, r.json()
    assert (r.json()["estado"], r.json()["estado_fisico"], r.json()["motivo_baja"]) == (
        "DISPONIBLE",
        "REGULAR",
        None,
    )
    detalle = _ejemplar(cliente, mundo, falta["id"])
    assert detalle["recuperable"] is False
    ultimo = detalle["historial"][-1]
    assert (ultimo["estado_anterior"], ultimo["estado_nuevo"]) == ("BAJA", "DISPONIBLE")
    assert ultimo["observacion"] == "Recuperado: Apareció en el depósito"
    [incidencia] = _detalle(cliente, mundo, remito)["incidencias"]
    assert incidencia["resuelta_en"] is not None
    assert incidencia["resolucion"] == "Recuperado: Apareció en el depósito"


@pytest.mark.ca("CA-CAT-21")
def test_una_baja_que_no_es_por_extravio_no_se_recupera(cliente, mundo):  # noqa: F811
    ej = mundo["ej_a"][2]
    baja = cliente.post(
        f"{API}/ejemplares/{ej['id']}/baja",
        json={"motivo": "Destruido por agua", "version": ej["version"]},
        headers=mundo["h_a"],
    ).json()

    _error(
        cliente.post(
            f"{API}/ejemplares/{ej['id']}/recuperar",
            json={
                "estado_fisico": "BUENO",
                "observacion": "Lo encontramos",
                "version": baja["version"],
            },
            headers=mundo["h_a"],
        ),
        409,
        "EJEMPLAR_NO_RECUPERABLE",
    )
    assert _ejemplar(cliente, mundo, ej["id"])["recuperable"] is False


def test_un_recuperado_danado_queda_en_revision(cliente, mundo):  # noqa: F811
    _, falta = _faltante(cliente, mundo)
    ejemplar = _ejemplar(cliente, mundo, falta["id"])

    r = cliente.post(
        f"{API}/ejemplares/{falta['id']}/recuperar",
        json={
            "estado_fisico": "DANADO",
            "observacion": "Apareció mojado",
            "version": ejemplar["version"],
        },
        headers=mundo["h_a"],
    )

    assert r.json()["estado"] == "EN_REVISION"


# --- R6. préstamos para armar el envío --------------------------------------------------------


def test_el_listado_de_prestamos_filtra_por_sede_origen(cliente, mundo):  # noqa: F811
    desde_a = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_a"][2]).json()
    _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][0])  # local en B

    r = cliente.get(
        f"{API}/prestamos",
        params={"sede_origen_id": mundo["a"]["id"], "estado": "SOLICITADO"},
        headers=mundo["h_a"],
    ).json()

    assert [p["id"] for p in r["items"]] == [desde_a["id"]]
