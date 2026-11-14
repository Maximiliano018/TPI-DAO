"""Reportes R1 a R6 de punta a punta contra PostgreSQL, con datos conocidos."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.controllers.test_devolucion_api import _devolver, _entregado
from tests.controllers.test_prestamo_api import (  # noqa: F401
    HOY,
    _avanzar,
    _prestar,
    _recibir,
    _remito,
    mundo,
)
from tests.controllers.test_sede_api import _error

API = "/api/v1/reportes"


def _traslado(cliente, m, destino, *ejemplares):
    lineas = [{"ejemplar_id": e["id"]} for e in ejemplares]
    remito = _remito(cliente, m["h_a"], m[destino], lineas, motivo="TRASLADO").json()
    return _avanzar(cliente, m["h_a"], remito, "empaquetar", "despachar")


def _con_transito(sesion, remito, dias):
    """Mueve el despacho al pasado y deja la recepción ``dias`` después."""
    sesion.execute(
        text(
            "UPDATE remito SET fecha_despacho = now() - interval '10 days', "
            "fecha_recepcion = now() - interval '10 days' + make_interval(days => :d) "
            "WHERE id = :id"
        ),
        {"d": dias, "id": remito["id"]},
    )
    sesion.commit()


def _remito_sql(sesion, m, numero, estado, destino="b", despacho=True):
    sesion.execute(
        text(
            "INSERT INTO remito (numero, sede_origen_id, sede_destino_id, motivo, estado, "
            "fecha_generacion, fecha_despacho, version) VALUES (:n, :o, :d, 'TRASLADO', :e, "
            "now() - interval '3 days', CASE WHEN :desp THEN now() - interval '2 days' END, 1)"
        ),
        {
            "n": numero,
            "o": m["a"]["id"],
            "d": m[destino]["id"],
            "e": estado,
            "desp": despacho,
        },
    )


def _prestamo_sql(sesion, m, numero, ejemplar, estado, tipo="INTERBIBLIOTECARIO", destino="b"):
    # La base exige fechas coherentes con el estado (ck_prestamo_fechas_segun_estado).
    entregado = estado in ("ACTIVO", "VENCIDO", "DEVUELTO")
    sesion.execute(
        text(
            "INSERT INTO prestamo (numero, socio_id, ejemplar_id, tipo, sede_origen_id, "
            "sede_destino_id, estado, fecha_solicitud, renovaciones, fecha_inicio, "
            "fecha_vencimiento, fecha_devolucion) "
            "VALUES (:n, :s, :e, :t, :o, :d, :estado, now(), 0, "
            "CASE WHEN :entregado THEN current_date END, "
            "CASE WHEN :entregado THEN current_date + 14 END, "
            "CASE WHEN :devuelto THEN now() END)"
        ),
        {
            "n": numero,
            "s": m["juan"]["id"],
            "e": ejemplar["id"],
            "t": tipo,
            "o": m["a"]["id"],
            "d": m[destino if tipo == "INTERBIBLIOTECARIO" else "a"]["id"],
            "estado": estado,
            "entregado": entregado,
            "devuelto": estado == "DEVUELTO",
        },
    )


# --- R1 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-01", "CA-REP-02", "CA-REP-03")
def test_r1_promedia_el_transito_por_ruta(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_a"]
    de_tres = _traslado(cliente, mundo, "b", ej[1], ej[2], ej[3])
    de_uno = _traslado(cliente, mundo, "b", ej[4])
    for remito, ejemplares in ((de_tres, ej[1:4]), (de_uno, [ej[4]])):
        lineas = [(e["id"], "BUENO", {}) for e in ejemplares]
        assert _recibir(cliente, mundo["h_b"], remito, *lineas).status_code == 200
    _con_transito(sesion, de_tres, 2)
    _con_transito(sesion, de_uno, 4)
    _traslado(cliente, mundo, "c", ej[0])  # sigue en tránsito: no entra

    r = cliente.get(f"{API}/movimiento-entre-sedes", headers=mundo["h_admin"])

    assert r.status_code == 200, r.json()
    assert [
        (x["sede_origen"], x["sede_destino"], x["envios"], x["ejemplares"])
        for x in r.json()["rutas"]
    ] == [("Sede SEDE_A", "Sede SEDE_B", 2, 4)]
    assert r.json()["rutas"][0]["tiempo_promedio_transito_dias"] == 3.0
    assert (r.json()["total_envios"], r.json()["total_ejemplares"]) == (2, 4)
    # El bibliotecario queda en su sede (B) aunque pida otra: ve la ruta A → B.
    h_c = cliente.get(
        f"{API}/movimiento-entre-sedes",
        params={"sede_id": mundo["a"]["id"]},
        headers=mundo["h_b"],
    )
    assert h_c.json()["total_envios"] == 2


@pytest.mark.ca("CA-REP-14", "CA-REP-15")
def test_un_rango_invertido_se_rechaza_y_sin_datos_no_es_error(cliente, mundo):  # noqa: F811
    antes = (HOY - timedelta(days=30)).isoformat()
    hoy = HOY.isoformat()
    for ruta in ("movimiento-entre-sedes", "envios-e-incidencias", "libros-mas-solicitados"):
        _error(
            cliente.get(
                f"{API}/{ruta}", params={"desde": hoy, "hasta": antes}, headers=mundo["h_admin"]
            ),
            422,
            "VALIDACION",
        )
    vacio = cliente.get(
        f"{API}/movimiento-entre-sedes",
        params={"desde": antes, "hasta": antes},
        headers=mundo["h_admin"],
    )
    assert vacio.status_code == 200
    assert vacio.json()["rutas"] == []
    envios = cliente.get(f"{API}/envios-e-incidencias", headers=mundo["h_admin"]).json()
    assert (envios["total_envios"], envios["tasa_exito"]) == (0, None)


# --- R2 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-04", "CA-REP-05", "CA-REP-12")
def test_r2_calcula_la_tasa_de_exito_sin_anulados_ni_abiertos(cliente, mundo, sesion):  # noqa: F811
    for i in range(8):
        _remito_sql(sesion, mundo, f"T-{i}", "RECIBIDO", destino="b" if i < 5 else "c")
    _remito_sql(sesion, mundo, "T-EXT", "EXTRAVIADO")
    _remito_sql(sesion, mundo, "T-DAN", "DANADO")
    _remito_sql(sesion, mundo, "T-ANU", "ANULADO", despacho=False)
    _remito_sql(sesion, mundo, "T-ABI", "EN_TRANSITO")
    sesion.commit()

    r = cliente.get(f"{API}/envios-e-incidencias", headers=mundo["h_admin"]).json()

    assert (r["total_envios"], r["recibidos"], r["extraviados"], r["danados"]) == (10, 8, 1, 1)
    assert (r["tasa_exito"], r["tasa_incidencias"]) == (0.8, 0.2)
    assert [(s["sede"], s["total_envios"]) for s in r["por_sede"]] == [("Sede SEDE_A", 10)]
    de_c = cliente.get(
        f"{API}/envios-e-incidencias",
        params={"sede_id": mundo["c"]["id"]},
        headers=mundo["h_admin"],
    ).json()
    assert (de_c["total_envios"], de_c["tasa_exito"]) == (3, 1.0)
    for ruta in ("envios-e-incidencias", "libros-mas-solicitados"):
        _error(cliente.get(f"{API}/{ruta}", headers=mundo["h_b"]), 403, "FORBIDDEN")


# --- R3 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-06", "CA-REP-07")
def test_r3_ordena_por_prestamos_entre_sedes_no_cancelados(cliente, mundo, sesion):  # noqa: F811
    x, y, local = mundo["ej_a"][0], mundo["ej_a"][1], mundo["ej_a"][2]
    for i in range(4):
        _prestamo_sql(sesion, mundo, f"X-{i}", x, "DEVUELTO")
    _prestamo_sql(sesion, mundo, "X-CAN", x, "CANCELADO")
    for i, destino in enumerate(("c", "c", "b")):
        _prestamo_sql(sesion, mundo, f"Y-{i}", y, "DEVUELTO", destino=destino)
    for i in range(6):
        _prestamo_sql(sesion, mundo, f"L-{i}", local, "DEVUELTO", tipo="LOCAL")
    sesion.commit()

    r = cliente.get(f"{API}/libros-mas-solicitados", headers=mundo["h_admin"]).json()

    assert [(x["titulo"], x["prestamos"]) for x in r["libros"]] == [("Libro 0", 4), ("Libro 1", 3)]
    assert (r["libros"][0]["posicion"], r["libros"][0]["sede_origen_frecuente"]) == (
        1,
        "Sede SEDE_A",
    )
    assert r["libros"][1]["sede_destino_frecuente"] == "Sede SEDE_C"
    uno = cliente.get(
        f"{API}/libros-mas-solicitados", params={"limite": 1}, headers=mundo["h_admin"]
    ).json()
    assert len(uno["libros"]) == 1


# --- R4 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-08", "CA-REP-09")
def test_r4_muestra_el_atraso_y_la_multa_acumulada(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(4)
    )

    r = cliente.get(f"{API}/vencidos-y-multas", headers=mundo["h_admin"]).json()

    assert [(v["numero"], v["dias_atraso"], v["multa_acumulada"]) for v in r["vencidos"]] == [
        (p["numero"], 4, "800.00")
    ]
    assert (r["total_adeudado"], r["multas"]) == ("800.00", [])
    # El bibliotecario de otra sede no ve el vencido de B.
    ajeno = cliente.get(f"{API}/vencidos-y-multas", headers=mundo["h_a"]).json()
    assert ajeno["vencidos"] == []

    _devolver(cliente, mundo["h_b"], p)
    despues = cliente.get(f"{API}/vencidos-y-multas", headers=mundo["h_b"]).json()

    assert despues["vencidos"] == []
    assert [(x["numero_prestamo"], x["estado"], x["monto_total"]) for x in despues["multas"]] == [
        (p["numero"], "PENDIENTE", "800.00")
    ]
    assert (despues["total_multas_pendientes"], despues["total_adeudado"]) == ("800.00", "800.00")
    _error(cliente.get(f"{API}/vencidos-y-multas", headers=mundo["h_lucia"]), 403, "FORBIDDEN")


# --- R5 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-10")
def test_r5_cuenta_los_ejemplares_por_estado_en_cada_sede(cliente, mundo, sesion):  # noqa: F811
    libro = mundo["libros"][0]
    cliente.post(
        "/api/v1/ejemplares",
        json={"libro_id": libro["id"], "codigo_inventario": "A-0-BIS", "sede_id": mundo["a"]["id"]},
        headers=mundo["h_admin"],
    )
    _entregado(cliente, sesion, mundo["h_a"], mundo["lucia"], mundo["ej_a"][0])

    r = cliente.get(
        f"{API}/disponibilidad-por-sede",
        params={"libro_id": libro["id"]},
        headers=mundo["h_lucia"],
    )

    assert r.status_code == 200, r.json()
    filas = {f["sede"]: f for f in r.json()["items"]}
    a = filas["Sede SEDE_A"]
    assert (a["totales"], a["disponibles"], a["prestados"]) == (2, 1, 1)
    assert (filas["Sede SEDE_B"]["totales"], r.json()["total"]) == (1, 2)


# --- R6 --------------------------------------------------------------------------------------


@pytest.mark.ca("CA-REP-11", "CA-REP-13")
def test_r6_lista_prestamos_activos_y_remitos_abiertos_de_la_sede(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0])
    remito = _traslado(cliente, mundo, "c", mundo["ej_a"][1])

    todo = cliente.get(f"{API}/prestamos-activos-y-en-transito", headers=mundo["h_admin"]).json()
    de_a = cliente.get(
        f"{API}/prestamos-activos-y-en-transito",
        params={"sede_id": mundo["b"]["id"]},
        headers=mundo["h_a"],
    ).json()

    assert [(x["numero"], x["estado"], x["dias_para_vencer"]) for x in todo["prestamos"]] == [
        (p["numero"], "ACTIVO", 14)
    ]
    assert [(x["numero"], x["estado"], x["antiguedad_dias"]) for x in todo["remitos"]] == [
        (remito["numero"], "DESPACHADO", 0)
    ]
    assert de_a["prestamos"] == []
    assert [x["numero"] for x in de_a["remitos"]] == [remito["numero"]]
    _error(
        cliente.get(f"{API}/prestamos-activos-y-en-transito", headers=mundo["h_lucia"]),
        403,
        "FORBIDDEN",
    )
