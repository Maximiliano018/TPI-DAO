"""Devoluciones y multas de punta a punta contra PostgreSQL."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, text

from app.db.models import IncidenciaORM
from tests.controllers.test_prestamo_api import (  # noqa: F401
    HOY,
    _avanzar,
    _estado_ejemplar,
    _prestar,
    _recibir,
    _remito,
    mundo,
)
from tests.controllers.test_sede_api import _error

API = "/api/v1"
ZONA = ZoneInfo("America/Argentina/Cordoba")


def _entregado(cliente, sesion, headers, socio, ejemplar, *, vence=None):
    """Préstamo local entregado; con ``vence`` se mueve el plazo hacia atrás."""
    p = _prestar(cliente, headers, socio, ejemplar).json()
    r = cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=headers)
    assert r.status_code == 200, r.json()
    if vence is not None:
        sesion.execute(
            text("UPDATE prestamo SET fecha_inicio = :i, fecha_vencimiento = :v WHERE id = :id"),
            {"i": vence - timedelta(days=14), "v": vence, "id": p["id"]},
        )
        sesion.commit()
    return p


def _devolver(cliente, headers, prestamo, estado="BUENO", **extra):
    cuerpo = {"estado_fisico": estado, **extra}
    url = f"{API}/prestamos/{prestamo['id']}/devolucion"
    return cliente.post(url, json=cuerpo, headers=headers)


def _ficha(cliente, m, socio):
    return cliente.get(f"{API}/socios/{socio['id']}", headers=m["h_admin"]).json()


def _vencidos(cliente, m):
    r = cliente.post(f"{API}/admin/tareas/detectar-vencidos", headers=m["h_admin"])
    assert r.status_code == 200, r.json()


def _incidencias(sesion, prestamo):
    sesion.expire_all()
    return [
        (i.tipo, i.origen, i.socio_id)
        for i in sesion.scalars(
            select(IncidenciaORM).where(IncidenciaORM.prestamo_id == prestamo["id"])
        )
    ]


# --- devolución local ------------------------------------------------------------------------


@pytest.mark.ca("CA-DEV-01", "CA-DEV-11", "CA-DEV-05")
def test_devolucion_local_en_termino(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_b"][0]
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], ej, vence=HOY)

    r = _devolver(cliente, mundo["h_b"], p, "REGULAR", observaciones="Hojas marcadas")

    assert r.status_code == 201, r.json()
    cuerpo = r.json()
    assert cuerpo["prestamo"]["estado"] == "DEVUELTO"
    assert cuerpo["prestamo"]["fecha_devolucion"] is not None
    devolucion = cuerpo["devolucion"]
    assert (devolucion["estado_fisico_recibido"], devolucion["dias_atraso"]) == ("REGULAR", 0)
    assert cuerpo["devolucion"]["registrada_por"]["nombre"] == "Beto B"
    assert (cuerpo["multa"], cuerpo["remito_retorno"], cuerpo["socio"]["estado"]) == (
        None,
        None,
        "HABILITADO",
    )
    ejemplar = _estado_ejemplar(cliente, mundo, ej)
    assert (ejemplar["estado"], ejemplar["estado_fisico"], ejemplar["sede_actual_id"]) == (
        "DISPONIBLE",
        "REGULAR",
        mundo["b"]["id"],
    )
    detalle = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_lucia"]).json()
    assert detalle["devolucion"]["observaciones"] == "Hojas marcadas"
    assert detalle["multa"] is None


@pytest.mark.ca("CA-DEV-02", "CA-DEV-03", "CA-ACC-02", "CA-DEV-04")
def test_reglas_al_registrar_la_devolucion(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0])

    # Otra sede, el socio o el administrador no registran devoluciones.
    _error(_devolver(cliente, mundo["h_a"], p), 403, "FORBIDDEN")
    _error(_devolver(cliente, mundo["h_lucia"], p), 403, "FORBIDDEN")
    _error(_devolver(cliente, mundo["h_admin"], p), 403, "FORBIDDEN")
    futura = datetime.combine(HOY + timedelta(days=1), time(10), ZONA).isoformat()
    _error(_devolver(cliente, mundo["h_b"], p, fecha_hora=futura), 422, "VALIDACION")
    anterior = datetime.combine(HOY - timedelta(days=1), time(10), ZONA).isoformat()
    _error(_devolver(cliente, mundo["h_b"], p, fecha_hora=anterior), 422, "VALIDACION")
    _error(_devolver(cliente, mundo["h_b"], p, "DANADO"), 422, "VALIDACION")

    assert _devolver(cliente, mundo["h_b"], p).status_code == 201
    _error(_devolver(cliente, mundo["h_b"], p), 409, "TRANSICION_INVALIDA")
    otro = _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][1]).json()
    _error(_devolver(cliente, mundo["h_b"], otro), 409, "TRANSICION_INVALIDA")


# --- multas y habilitación del socio ---------------------------------------------------------


@pytest.mark.ca("CA-DEV-06", "CA-DEV-09", "CA-DEV-10", "CA-SOC-06", "CA-SOC-07")
def test_devolucion_tardia_genera_multa_y_se_rehabilita_al_saldarla(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(5)
    )
    _vencidos(cliente, mundo)
    assert _ficha(cliente, mundo, mundo["lucia"])["estado"] == "INHABILITADO"

    cuerpo = _devolver(cliente, mundo["h_b"], p).json()

    multa = cuerpo["multa"]
    assert (multa["dias_atraso"], multa["monto_por_dia"], multa["monto_total"]) == (
        5,
        "200.00",
        "1000.00",
    )
    assert multa["estado"] == "PENDIENTE"
    # Devolvió lo vencido pero debe la multa: sigue inhabilitado.
    socio = cuerpo["socio"]
    assert (socio["estado"], socio["motivo"]) == ("INHABILITADO", "MULTA_IMPAGA")
    ficha = _ficha(cliente, mundo, mundo["lucia"])
    assert (ficha["estado"], ficha["motivo_inhabilitacion"]) == ("INHABILITADO", "MULTA_IMPAGA")
    assert ficha["situacion"]["multas_pendientes"] == 1
    _error(
        _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][1]), 409, "SOCIO_INHABILITADO"
    )
    _error(
        cliente.post(
            f"{API}/socios/{mundo['lucia']['id']}/baja",
            json={"motivo": "Pidió la baja"},
            headers=mundo["h_admin"],
        ),
        409,
        "SOCIO_CON_ACTIVIDAD_PENDIENTE",
    )

    _error(
        cliente.post(f"{API}/multas/{multa['id']}/saldar", headers=mundo["h_lucia"]),
        403,
        "FORBIDDEN",
    )
    saldada = cliente.post(f"{API}/multas/{multa['id']}/saldar", headers=mundo["h_a"]).json()

    assert (saldada["estado"], saldada["saldada_por"]["nombre"]) == ("SALDADA", "Bea A")
    assert _ficha(cliente, mundo, mundo["lucia"])["estado"] == "HABILITADO"
    _error(
        cliente.post(f"{API}/multas/{multa['id']}/saldar", headers=mundo["h_admin"]),
        409,
        "TRANSICION_INVALIDA",
    )
    _error(
        cliente.post(f"{API}/multas/999999/saldar", headers=mundo["h_admin"]),
        404,
        "MULTA_NO_ENCONTRADA",
    )


@pytest.mark.ca("CA-DEV-08")
def test_si_lo_devolvio_a_tiempo_pero_se_registra_despues_no_hay_multa(cliente, mundo, sesion):  # noqa: F811
    vence = HOY - timedelta(days=2)
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=vence)
    _vencidos(cliente, mundo)

    a_tiempo = datetime.combine(vence, time(18), ZONA).isoformat()
    cuerpo = _devolver(cliente, mundo["h_b"], p, fecha_hora=a_tiempo).json()

    assert (cuerpo["devolucion"]["dias_atraso"], cuerpo["multa"]) == (0, None)
    assert cuerpo["socio"]["estado"] == "HABILITADO"


@pytest.mark.ca("CA-DEV-07")
def test_la_multa_nueva_usa_el_monto_por_dia_vigente(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(3)
    )
    r = cliente.put(
        f"{API}/parametros/multa_por_dia", json={"valor": "350"}, headers=mundo["h_admin"]
    )
    assert r.status_code == 200, r.json()

    multa = _devolver(cliente, mundo["h_b"], p).json()["multa"]

    assert (multa["monto_por_dia"], multa["monto_total"]) == ("350.00", "1050.00")


@pytest.mark.ca("CA-DEV-16")
def test_el_socio_ve_solo_sus_multas(cliente, mundo, sesion):  # noqa: F811
    vencio = HOY - timedelta(days=1)
    de_lucia = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=vencio
    )
    de_juan = _entregado(
        cliente, sesion, mundo["h_b"], mundo["juan"], mundo["ej_b"][1], vence=vencio
    )
    _devolver(cliente, mundo["h_b"], de_lucia)
    _devolver(cliente, mundo["h_b"], de_juan)

    propias = cliente.get(f"{API}/multas", headers=mundo["h_lucia"]).json()
    ajenas = cliente.get(
        f"{API}/multas", params={"socio_id": mundo["juan"]["id"]}, headers=mundo["h_lucia"]
    ).json()
    todas = cliente.get(f"{API}/multas", headers=mundo["h_b"]).json()
    pendientes_juan = cliente.get(
        f"{API}/multas",
        params={"socio_id": mundo["juan"]["id"], "estado": "PENDIENTE"},
        headers=mundo["h_admin"],
    ).json()

    assert [m["socio_id"] for m in propias["items"]] == [mundo["lucia"]["id"]]
    assert propias["items"][0]["numero_prestamo"] == de_lucia["numero"]
    assert ajenas["total"] == 1 and ajenas["items"][0]["socio_id"] == mundo["lucia"]["id"]
    assert todas["total"] == 2
    assert [m["socio"] for m in pendientes_juan["items"]] == ["Juan Socio"]


# --- estado del ejemplar ---------------------------------------------------------------------


@pytest.mark.ca("CA-DEV-13")
def test_un_ejemplar_devuelto_danado_queda_en_revision_con_incidencia(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_b"][0]
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], ej)

    r = _devolver(cliente, mundo["h_b"], p, "DANADO", observaciones="Lomo despegado")

    assert r.status_code == 201, r.json()
    ejemplar = _estado_ejemplar(cliente, mundo, ej)
    assert (ejemplar["estado"], ejemplar["estado_fisico"]) == ("EN_REVISION", "DANADO")
    assert _incidencias(sesion, p) == [("DANIO", "DEVOLUCION", mundo["lucia"]["id"])]
    # Sin atraso no hay multa ni inhabilitación por el daño.
    assert r.json()["socio"]["estado"] == "HABILITADO"


@pytest.mark.ca("CA-DEV-14")
def test_un_ejemplar_extraviado_pasa_a_baja_con_incidencia(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_b"][0]
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], ej)

    r = _devolver(cliente, mundo["h_b"], p, "EXTRAVIADO", observaciones="Lo perdió en un viaje")

    assert r.json()["prestamo"]["estado"] == "DEVUELTO"
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "BAJA"
    assert _incidencias(sesion, p) == [("EXTRAVIO", "DEVOLUCION", mundo["lucia"]["id"])]


@pytest.mark.ca("CA-DEV-15")
def test_el_ejemplar_devuelto_se_asigna_a_la_reserva_pendiente(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_a"][2]  # único ejemplar del libro 2
    p = _entregado(cliente, sesion, mundo["h_a"], mundo["lucia"], ej)
    reserva = cliente.post(
        f"{API}/reservas",
        json={
            "libro_id": mundo["libros"][2]["id"],
            "sede_retiro_id": mundo["a"]["id"],
            "socio_id": mundo["juan"]["id"],
        },
        headers=mundo["h_a"],
    ).json()

    cuerpo = _devolver(cliente, mundo["h_a"], p).json()

    assert cuerpo["reserva_asignada"] == reserva["numero"]
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "RESERVADO"
    lista = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_a"]).json()
    assert (lista["estado"], lista["ejemplar_id"]) == ("DISPONIBLE_PARA_RETIRO", ej["id"])


# --- devolución interbibliotecaria -----------------------------------------------------------


def _interbibliotecario_entregado(cliente, m, ej):
    p = _prestar(cliente, m["h_b"], m["lucia"], ej).json()
    ida = _remito(
        cliente, m["h_a"], m["b"], [{"ejemplar_id": ej["id"], "prestamo_id": p["id"]}]
    ).json()
    _avanzar(cliente, m["h_a"], ida, "empaquetar", "despachar")
    _recibir(cliente, m["h_b"], ida, (ej["id"], "BUENO", {}))
    r = cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=m["h_b"])
    assert r.status_code == 200, r.json()
    return p, ida


@pytest.mark.ca("CA-DEV-12")
def test_la_devolucion_entre_sedes_genera_el_remito_de_retorno(cliente, mundo):  # noqa: F811
    ej = mundo["ej_a"][0]
    p, ida = _interbibliotecario_entregado(cliente, mundo, ej)

    # La devolución se registra en la sede destino (B), no en la propietaria (A).
    _error(_devolver(cliente, mundo["h_a"], p), 403, "FORBIDDEN")
    cuerpo = _devolver(cliente, mundo["h_b"], p).json()

    retorno = cuerpo["remito_retorno"]
    assert retorno["numero"] != ida["numero"]
    assert (retorno["motivo"], retorno["estado"]) == ("RETORNO", "GENERADO")
    completo = cliente.get(f"{API}/remitos/{retorno['id']}", headers=mundo["h_b"]).json()
    assert (completo["sede_origen_id"], completo["sede_destino_id"]) == (
        mundo["b"]["id"],
        mundo["a"]["id"],
    )
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "APARTADO"
    detalle = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_lucia"]).json()
    assert [r["motivo"] for r in detalle["remitos"]] == ["ENVIO", "RETORNO"]

    _avanzar(cliente, mundo["h_b"], completo, "empaquetar", "despachar")
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "EN_TRANSITO"
    assert _recibir(cliente, mundo["h_a"], completo, (ej["id"], "BUENO", {})).status_code == 200
    en_casa = _estado_ejemplar(cliente, mundo, ej)
    assert (en_casa["estado"], en_casa["sede_actual_id"]) == ("DISPONIBLE", mundo["a"]["id"])


def test_el_danado_entre_sedes_vuelve_y_se_revisa_en_su_sede(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_a"][0]
    p, _ = _interbibliotecario_entregado(cliente, mundo, ej)

    cuerpo = _devolver(cliente, mundo["h_b"], p, "DANADO", observaciones="Mojado").json()

    retorno = cliente.get(
        f"{API}/remitos/{cuerpo['remito_retorno']['id']}", headers=mundo["h_b"]
    ).json()
    _avanzar(cliente, mundo["h_b"], retorno, "empaquetar", "despachar")
    _recibir(cliente, mundo["h_a"], retorno, (ej["id"], "DANADO", {"observacion": "Mojado"}))
    en_casa = _estado_ejemplar(cliente, mundo, ej)
    assert (en_casa["estado"], en_casa["sede_actual_id"]) == ("EN_REVISION", mundo["a"]["id"])
    # El daño se registró una sola vez, en la devolución.
    assert _incidencias(sesion, p) == [("DANIO", "DEVOLUCION", mundo["lucia"]["id"])]
