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
    # La base exige fechas coherentes con el estado (ck_remito_*_segun_estado).
    recibido = estado in ("RECIBIDO", "DANADO", "DESTRUIDO", "INCOMPLETO")
    sesion.execute(
        text(
            "INSERT INTO remito (numero, sede_origen_id, sede_destino_id, motivo, estado, "
            "fecha_generacion, fecha_despacho, fecha_recepcion, version) "
            "VALUES (:n, :o, :d, 'TRASLADO', :e, now() - interval '3 days', "
            "CASE WHEN :desp THEN now() - interval '2 days' END, "
            "CASE WHEN :recibido THEN now() - interval '1 day' END, 1)"
        ),
        {
            "n": numero,
            "o": m["a"]["id"],
            "d": m[destino]["id"],
            "e": estado,
            "desp": despacho,
            "recibido": recibido,
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
            "CASE WHEN :entregado THEN CAST(:hoy AS date) END, "
            "CASE WHEN :entregado THEN CAST(:hoy AS date) + 14 END, "
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
            "hoy": HOY,
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
    _remito_sql(sesion, mundo, "T-INC", "INCOMPLETO")  # recibido con faltantes
    _remito_sql(sesion, mundo, "T-ANU", "ANULADO", despacho=False)
    _remito_sql(sesion, mundo, "T-ABI", "EN_TRANSITO")
    sesion.commit()

    r = cliente.get(f"{API}/envios-e-incidencias", headers=mundo["h_admin"]).json()

    assert (r["total_envios"], r["recibidos"], r["extraviados"], r["danados"]) == (11, 8, 1, 1)
    assert r["incompletos"] == 1
    assert (r["tasa_exito"], r["tasa_incidencias"]) == (0.7273, 0.2727)
    assert [(s["sede"], s["total_envios"]) for s in r["por_sede"]] == [("Sede SEDE_A", 11)]
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


@pytest.mark.ca("CA-REP-08", "CA-REP-09", "CA-REP-23")
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


@pytest.mark.ca("CA-REP-10", "CA-REP-23")
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


@pytest.mark.ca("CA-REP-11", "CA-REP-13", "CA-REP-23")
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


# --- Filtros y correcciones (CA-REP-16 a 21) ------------------------------------------------


def _vencido_entre_sedes(sesion, m, numero, ejemplar, dias, estado="VENCIDO"):
    """Préstamo A → B de Juan vencido hace ``dias`` (con ``estado`` ACTIVO, la tarea diaria
    todavía no lo marcó)."""
    _prestamo_sql(sesion, m, numero, ejemplar, estado, destino="b")
    sesion.execute(
        text("UPDATE prestamo SET fecha_vencimiento = CAST(:v AS date) WHERE numero = :n"),
        {"v": HOY - timedelta(days=dias), "n": numero},
    )
    sesion.commit()


def _r(cliente, m, ruta, headers="h_admin", **params):
    r = cliente.get(f"{API}/{ruta}", params=params, headers=m[headers])
    assert r.status_code == 200, r.json()
    return r.json()


@pytest.mark.ca("CA-REP-16")
def test_r1_filtra_por_motivo_origen_y_destino(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_a"]
    a_b = _traslado(cliente, mundo, "b", ej[1])
    assert _recibir(cliente, mundo["h_b"], a_b, (ej[1]["id"], "BUENO", {})).status_code == 200
    a_c = _traslado(cliente, mundo, "c", ej[2])
    # La sede C no tiene bibliotecario: se da por recibido en la base.
    sesion.execute(
        text("UPDATE remito SET estado = 'RECIBIDO', fecha_recepcion = now() WHERE id = :id"),
        {"id": a_c["id"]},
    )
    sesion.commit()

    def rutas(**params):
        datos = _r(cliente, mundo, "movimiento-entre-sedes", **params)
        return [(x["sede_origen"], x["sede_destino"]) for x in datos["rutas"]]

    assert len(rutas(motivo="TRASLADO")) == 2
    assert rutas(motivo="RETORNO") == []
    assert rutas(sede_destino_id=mundo["c"]["id"]) == [("Sede SEDE_A", "Sede SEDE_C")]
    assert rutas(sede_origen_id=mundo["b"]["id"]) == []


@pytest.mark.ca("CA-REP-17")
def test_r1_no_cuenta_los_faltantes_como_movidos(cliente, mundo):  # noqa: F811
    ej = mundo["ej_a"]
    remito = _traslado(cliente, mundo, "b", ej[1], ej[2])
    falta = {"faltante": True, "observacion": "No venía en la caja"}
    r = _recibir(
        cliente, mundo["h_b"], remito, (ej[1]["id"], "BUENO", {}), (ej[2]["id"], None, falta)
    )
    assert r.json()["estado"] == "INCOMPLETO"

    datos = _r(cliente, mundo, "movimiento-entre-sedes")

    assert (datos["total_envios"], datos["total_ejemplares"]) == (1, 1)


@pytest.mark.ca("CA-REP-21")
def test_r2_detalla_por_sede_destino(cliente, mundo, sesion):  # noqa: F811
    for i in range(3):
        _remito_sql(sesion, mundo, f"D-B-{i}", "RECIBIDO", destino="b")
    _remito_sql(sesion, mundo, "D-C-0", "EXTRAVIADO", destino="c")
    sesion.commit()

    datos = _r(cliente, mundo, "envios-e-incidencias")

    assert [(s["sede"], s["total_envios"]) for s in datos["por_sede"]] == [("Sede SEDE_A", 4)]
    assert [(s["sede"], s["total_envios"], s["tasa_exito"]) for s in datos["por_destino"]] == [
        ("Sede SEDE_B", 3, 1.0),
        ("Sede SEDE_C", 1, 0.0),
    ]


@pytest.mark.ca("CA-REP-16")
def test_r3_filtra_por_la_sede_que_interviene(cliente, mundo, sesion):  # noqa: F811
    x, y = mundo["ej_a"][0], mundo["ej_a"][1]
    for i in range(4):
        _prestamo_sql(sesion, mundo, f"X-{i}", x, "DEVUELTO", destino="b")
    for i in range(2):
        _prestamo_sql(sesion, mundo, f"Y-{i}", y, "DEVUELTO", destino="c")
    sesion.commit()

    datos = _r(cliente, mundo, "libros-mas-solicitados", sede_id=mundo["c"]["id"])

    assert [(x["titulo"], x["prestamos"]) for x in datos["libros"]] == [("Libro 1", 2)]


@pytest.mark.ca("CA-REP-18")
def test_r4_el_total_adeudado_no_depende_de_los_filtros_de_la_lista(cliente, mundo, sesion):  # noqa: F811
    p = _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(4)
    )
    _devolver(cliente, mundo["h_b"], p)  # multa pendiente de $800
    _vencido_entre_sedes(sesion, mundo, "IB-1", mundo["ej_a"][0], 2)  # $400 acumulados
    viejo = (HOY - timedelta(days=60)).isoformat()
    ruta = "vencidos-y-multas"

    for params in (
        {},
        {"estado_multa": "SALDADA"},
        {"desde": viejo, "hasta": viejo},
        {"atraso_min": 5},
    ):
        datos = _r(cliente, mundo, ruta, **params)
        assert (datos["total_multas_pendientes"], datos["total_acumulado_vencidos"]) == (
            "800.00",
            "400.00",
        ), params
        assert (datos["total_adeudado"], datos["cantidad_vencidos"]) == ("1200.00", 1), params

    assert _r(cliente, mundo, ruta, estado_multa="SALDADA")["multas"] == []
    filtrado = _r(cliente, mundo, ruta, atraso_min=3, atraso_max=4)
    assert (filtrado["vencidos"], len(filtrado["multas"])) == ([], 1)
    _error(
        cliente.get(
            f"{API}/{ruta}", params={"atraso_min": 5, "atraso_max": 2}, headers=mundo["h_admin"]
        ),
        422,
        "VALIDACION",
    )


@pytest.mark.ca("CA-REP-16")
def test_r4_filtra_por_socio(cliente, mundo, sesion):  # noqa: F811
    _entregado(
        cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0], vence=HOY - timedelta(4)
    )
    _vencido_entre_sedes(sesion, mundo, "IB-1", mundo["ej_a"][0], 2)

    de_juan = _r(cliente, mundo, "vencidos-y-multas", socio_id=mundo["juan"]["id"])

    assert [v["numero"] for v in de_juan["vencidos"]] == ["IB-1"]
    assert de_juan["total_adeudado"] == "400.00"


@pytest.mark.ca("CA-REP-19")
def test_r4_la_sede_duena_ve_su_ejemplar_vencido_en_otra_sede(cliente, mundo, sesion):  # noqa: F811
    _vencido_entre_sedes(sesion, mundo, "IB-1", mundo["ej_a"][0], 3)

    de_a = _r(cliente, mundo, "vencidos-y-multas", headers="h_a")
    de_c = _r(cliente, mundo, "vencidos-y-multas", sede_id=mundo["c"]["id"])

    assert [(v["numero"], v["sede_origen"], v["sede"]) for v in de_a["vencidos"]] == [
        ("IB-1", "Sede SEDE_A", "Sede SEDE_B")
    ]
    assert de_c["vencidos"] == []


@pytest.mark.ca("CA-REP-20")
def test_r5_cuenta_igual_que_la_ficha_del_libro(cliente, mundo, sesion):  # noqa: F811
    sesion.execute(
        text("UPDATE ejemplar SET estado = 'APARTADO' WHERE id = :id"),
        {"id": mundo["ej_a"][0]["id"]},
    )
    sesion.commit()
    libro_id = mundo["libros"][0]["id"]

    r5 = _r(cliente, mundo, "disponibilidad-por-sede", libro_id=libro_id)["items"]
    ficha = cliente.get(
        f"/api/v1/libros/{libro_id}/disponibilidad", headers=mundo["h_admin"]
    ).json()["por_sede"]

    claves = ("sede_id", "totales", "disponibles", "prestados", "reservados", "en_transito")
    assert [{k: f[k] for k in (*claves, "otros")} for f in r5] == [
        {k: f[k] for k in (*claves, "otros")} for f in ficha
    ]
    de_a = next(f for f in r5 if f["sede"] == "Sede SEDE_A")
    assert (de_a["reservados"], de_a["otros"]) == (0, 1)


@pytest.mark.ca("CA-REP-16")
def test_r5_busca_por_titulo(cliente, mundo):  # noqa: F811
    datos = _r(cliente, mundo, "disponibilidad-por-sede", q="libro 1")

    assert {f["titulo"] for f in datos["items"]} == {"Libro 1"}


@pytest.mark.ca("CA-REP-16")
def test_r6_filtra_por_estado_tipo_y_estado_del_remito(cliente, mundo, sesion):  # noqa: F811
    local = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0])
    # Vencido por fecha aunque la tarea diaria todavía no lo marcó.
    _vencido_entre_sedes(sesion, mundo, "IB-1", mundo["ej_a"][0], 2, estado="ACTIVO")
    remito = _traslado(cliente, mundo, "c", mundo["ej_a"][1])
    ruta = "prestamos-activos-y-en-transito"

    def numeros(**params):
        return [p["numero"] for p in _r(cliente, mundo, ruta, **params)["prestamos"]]

    assert numeros(estado="VENCIDO") == ["IB-1"]
    assert numeros(estado="ACTIVO") == [local["numero"]]
    assert numeros(tipo="INTERBIBLIOTECARIO") == ["IB-1"]
    assert _r(cliente, mundo, ruta, estado_remito="EN_TRANSITO")["remitos"] == []
    assert [
        x["numero"] for x in _r(cliente, mundo, ruta, estado_remito="DESPACHADO")["remitos"]
    ] == [remito["numero"]]


@pytest.mark.ca("CA-DEV-33")
def test_r4_muestra_la_multa_por_danio_con_su_concepto(cliente, mundo, sesion):  # noqa: F811
    cliente.put(
        "/api/v1/parametros/multa_por_danio", json={"valor": "3000"}, headers=mundo["h_admin"]
    )
    p = _entregado(cliente, sesion, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0])
    _devolver(cliente, mundo["h_b"], p, "DANADO", observaciones="Lomo roto")

    datos = _r(cliente, mundo, "vencidos-y-multas")

    assert [(m["tipo"], m["concepto"], m["dias_atraso"]) for m in datos["multas"]] == [
        ("DANIO", "Daño del ejemplar", None)
    ]
    assert (datos["total_multas_pendientes"], datos["total_adeudado"]) == ("3000.00", "3000.00")
    # No tiene atraso: un rango de atraso la deja fuera de la lista, no del total.
    con_atraso = _r(cliente, mundo, "vencidos-y-multas", atraso_min=0)
    assert (con_atraso["multas"], con_atraso["total_adeudado"]) == ([], "3000.00")
