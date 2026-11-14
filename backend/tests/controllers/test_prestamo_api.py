"""Préstamos y remitos de punta a punta contra PostgreSQL."""

from datetime import timedelta

import pytest
from sqlalchemy import select, text

from app.db.models import CategoriaORM, LocalidadORM
from tests.controllers.test_sede_api import _alta, _error
from tests.fakes.reloj import HOY_DE_PRUEBAS

API = "/api/v1"
HOY = HOY_DE_PRUEBAS


@pytest.fixture
def mundo(cliente, sesion, crear_usuario, autenticar):
    """Dos sedes con su bibliotecario, un socio con cuenta, un libro y ejemplares en ambas."""
    admin = crear_usuario("ADMIN", nombre="Ana Admin", username="ana.admin")
    h_admin = autenticar(admin)
    localidad = sesion.scalar(select(LocalidadORM.id).where(LocalidadORM.nombre == "Córdoba"))
    categoria = sesion.scalar(select(CategoriaORM.id).limit(1))

    def sede(codigo, numero):
        return _alta(
            cliente,
            h_admin,
            localidad,
            codigo=codigo,
            nombre=f"Sede {codigo}",
            calle=f"Calle {codigo}",
            numero=numero,
        ).json()

    a, b, c = sede("SEDE_A", "1"), sede("SEDE_B", "2"), sede("SEDE_C", "3")
    h_a = autenticar(crear_usuario("BIBLIOTECARIO", sede_id=a["id"], nombre="Bea A"))
    h_b = autenticar(crear_usuario("BIBLIOTECARIO", sede_id=b["id"], nombre="Beto B"))

    def socio(documento, nombre):
        return cliente.post(
            f"{API}/socios",
            json={
                "tipo_documento": "DNI",
                "nro_documento": documento,
                "nombre": nombre,
                "apellido": "Socio",
                "email": f"{documento}@example.com",
            },
            headers=h_b,
        ).json()

    lucia = socio("30111222", "Lucía")
    cliente.post(
        f"{API}/socios/{lucia['id']}/cuenta",
        json={"username": "lucia", "password": "Clave-segura-123"},
        headers=h_b,
    )
    token = cliente.post(
        f"{API}/auth/login", json={"username": "lucia", "password": "Clave-segura-123"}
    ).json()
    libros = [
        cliente.post(
            f"{API}/libros",
            json={
                "titulo": f"Libro {i}",
                "autores": [f"Autor {i}"],
                "categoria_id": categoria,
            },
            headers=h_admin,
        ).json()
        for i in range(5)
    ]

    def ejemplar(libro, sede_dueña, codigo):
        return cliente.post(
            f"{API}/ejemplares",
            json={
                "libro_id": libro["id"],
                "codigo_inventario": codigo,
                "sede_id": sede_dueña["id"],
            },
            headers=h_admin,
        ).json()

    return {
        "h_admin": h_admin,
        "h_a": h_a,
        "h_b": h_b,
        "a": a,
        "b": b,
        "c": c,
        "lucia": lucia,
        "h_lucia": {"Authorization": f"Bearer {token['access_token']}"},
        "juan": socio("40111222", "Juan"),
        "libros": libros,
        "ej_a": [ejemplar(libros[i], a, f"A-{i}") for i in range(5)],
        "ej_b": [ejemplar(libros[i], b, f"B-{i}") for i in range(2)],
    }


def _prestar(cliente, headers, socio, ejemplar, **over):
    datos = {"socio_id": socio["id"], "ejemplar_id": ejemplar["id"], **over}
    return cliente.post(f"{API}/prestamos", json=datos, headers=headers)


def _estado_ejemplar(cliente, m, ejemplar):
    return cliente.get(f"{API}/ejemplares/{ejemplar['id']}", headers=m["h_admin"]).json()


def _remito(cliente, headers, destino, lineas, motivo="ENVIO"):
    return cliente.post(
        f"{API}/remitos",
        json={
            "sede_destino_id": destino["id"],
            "motivo": motivo,
            "lineas": lineas,
        },
        headers=headers,
    )


def _avanzar(cliente, headers, remito, *acciones):
    for accion in acciones:
        r = cliente.post(f"{API}/remitos/{remito['id']}/{accion}", headers=headers)
        assert r.status_code == 200, r.json()
    return r.json()


def _recibir(cliente, headers, remito, *lineas):
    cuerpo = {"lineas": [{"ejemplar_id": e, "estado_fisico": f, **x} for e, f, x in lineas]}
    return cliente.post(f"{API}/remitos/{remito['id']}/recibir", json=cuerpo, headers=headers)


# --- préstamo local --------------------------------------------------------------------------


@pytest.mark.ca("CA-PRE-08", "CA-PRE-10")
def test_prestamo_local_se_registra_y_se_entrega(cliente, mundo):
    ej = mundo["ej_b"][0]
    r = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej)

    assert r.status_code == 201, r.json()
    p = r.json()
    assert (p["tipo"], p["estado"], p["sede_origen_id"], p["sede_destino_id"]) == (
        "LOCAL",
        "SOLICITADO",
        mundo["b"]["id"],
        mundo["b"]["id"],
    )
    assert p["numero"].startswith(f"P-{HOY.year}-")
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "APARTADO"

    entregado = cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"]).json()
    assert entregado["estado"] == "ACTIVO"
    assert entregado["fecha_vencimiento"] == str(HOY + timedelta(days=14))
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "PRESTADO"


@pytest.mark.ca("CA-PRE-15")
def test_cancelar_un_solicitado_libera_el_ejemplar(cliente, mundo):
    ej = mundo["ej_b"][0]
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej).json()

    r = cliente.post(f"{API}/prestamos/{p['id']}/cancelar", json={}, headers=mundo["h_b"])

    assert r.json()["estado"] == "CANCELADO"
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "DISPONIBLE"


# --- reglas al registrar ---------------------------------------------------------------------


@pytest.mark.ca("CA-PRE-07", "CA-PRE-01")
def test_un_ejemplar_apartado_no_se_presta_a_otro_socio(cliente, mundo):
    ej = mundo["ej_b"][0]
    _prestar(cliente, mundo["h_b"], mundo["lucia"], ej)

    _error(_prestar(cliente, mundo["h_b"], mundo["juan"], ej), 409, "EJEMPLAR_NO_DISPONIBLE")


@pytest.mark.ca("CA-PRE-02", "CA-SOC-04")
def test_un_socio_inhabilitado_no_recibe_prestamos(cliente, mundo):
    cliente.post(
        f"{API}/socios/{mundo['juan']['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )

    error = _error(
        _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][0]), 409, "SOCIO_INHABILITADO"
    )
    assert "decisión administrativa" in error["mensaje"]


@pytest.mark.ca("CA-PRE-03")
def test_el_ejemplar_tiene_que_ser_de_la_sede_origen(cliente, mundo):
    r = _prestar(
        cliente, mundo["h_b"], mundo["lucia"], mundo["ej_a"][0], sede_origen_id=mundo["b"]["id"]
    )

    _error(r, 422, "EJEMPLAR_FUERA_DE_SEDE_ORIGEN")


@pytest.mark.ca("CA-PRE-06")
def test_el_cuarto_prestamo_simultaneo_se_rechaza(cliente, mundo):
    for i in range(3):
        assert _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_a"][i]).status_code == 201

    _error(
        _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_a"][3]), 409, "LIMITE_PRESTAMOS"
    )


@pytest.mark.ca("CA-ACC-01")
def test_un_socio_no_registra_prestamos_y_el_bibliotecario_solo_para_su_sede(cliente, mundo):
    _error(_prestar(cliente, mundo["h_lucia"], mundo["lucia"], mundo["ej_b"][0]), 403, "FORBIDDEN")
    _error(
        _prestar(
            cliente,
            mundo["h_b"],
            mundo["lucia"],
            mundo["ej_b"][0],
            sede_destino_id=mundo["a"]["id"],
        ),
        403,
        "FORBIDDEN",
    )


# --- préstamo interbibliotecario con su remito ----------------------------------------------


@pytest.mark.ca(
    "CA-PRE-11",
    "CA-PRE-09",
    "CA-REM-01",
    "CA-REM-07",
    "CA-REM-08",
    "CA-REM-09",
    "CA-REM-10",
    "CA-ACC-04",
)
def test_prestamo_entre_sedes_de_punta_a_punta(cliente, mundo):
    ej = mundo["ej_a"][0]
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej).json()
    assert (p["tipo"], p["sede_origen_id"], p["sede_destino_id"]) == (
        "INTERBIBLIOTECARIO",
        mundo["a"]["id"],
        mundo["b"]["id"],
    )
    _error(
        cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"]),
        409,
        "EJEMPLAR_NO_RECIBIDO",
    )

    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"], "prestamo_id": p["id"]}]
    ).json()
    otro = _remito(
        cliente,
        mundo["h_a"],
        mundo["c"],
        [{"ejemplar_id": mundo["ej_a"][1]["id"]}],
        motivo="TRASLADO",
    ).json()
    assert remito["numero"] != otro["numero"]
    detalle = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()
    assert detalle["estado"] == "EN_ENVIO"
    assert [r["numero"] for r in detalle["remitos"]] == [remito["numero"]]

    _error(
        cliente.post(f"{API}/remitos/{remito['id']}/empaquetar", headers=mundo["h_b"]),
        403,
        "FORBIDDEN",
    )
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar")
    _error(
        cliente.post(f"{API}/remitos/{remito['id']}/despachar", headers=mundo["h_b"]),
        403,
        "FORBIDDEN",
    )
    _avanzar(cliente, mundo["h_a"], remito, "despachar")
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "EN_TRANSITO"
    _error(
        cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"]),
        409,
        "EJEMPLAR_NO_RECIBIDO",
    )

    recibido = _recibir(cliente, mundo["h_b"], remito, (ej["id"], "BUENO", {}))
    assert recibido.status_code == 200, recibido.json()
    assert recibido.json()["estado"] == "RECIBIDO"
    en_destino = _estado_ejemplar(cliente, mundo, ej)
    assert (en_destino["estado"], en_destino["sede_actual_id"]) == ("APARTADO", mundo["b"]["id"])

    activo = cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"]).json()
    assert activo["estado"] == "ACTIVO"
    assert activo["fecha_vencimiento"] == str(HOY + timedelta(days=21))
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "PRESTADO"

    traza = cliente.get(f"{API}/remitos/{remito['id']}", headers=mundo["h_admin"]).json()
    assert [(m["estado_anterior"], m["estado_nuevo"]) for m in traza["movimientos"]] == [
        (None, "GENERADO"),
        ("GENERADO", "EMPAQUETADO"),
        ("EMPAQUETADO", "DESPACHADO"),
        ("DESPACHADO", "EN_TRANSITO"),
        ("EN_TRANSITO", "RECIBIDO"),
    ]
    assert traza["movimientos"][-1]["usuario"]["nombre"] == "Beto B"
    # El socio ve su préstamo y el estado del remito; no ve los de otros.
    propio = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_lucia"]).json()
    assert propio["remitos"][0]["estado"] == "RECIBIDO"
    listado = cliente.get(f"{API}/prestamos", headers=mundo["h_lucia"]).json()
    assert [x["id"] for x in listado["items"]] == [p["id"]]


@pytest.mark.ca("CA-REM-03")
def test_si_el_socio_no_retira_se_cancela_y_vuelve_con_otro_remito(cliente, mundo):
    ej = mundo["ej_a"][0]
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej).json()
    ida = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"], "prestamo_id": p["id"]}]
    ).json()
    _avanzar(cliente, mundo["h_a"], ida, "empaquetar", "despachar")
    _recibir(cliente, mundo["h_b"], ida, (ej["id"], "BUENO", {}))

    cancelado = cliente.post(
        f"{API}/prestamos/{p['id']}/cancelar",
        json={"motivo": "No vino a retirarlo"},
        headers=mundo["h_b"],
    )

    assert cancelado.json()["estado"] == "CANCELADO"
    remitos = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()["remitos"]
    assert [(r["motivo"], r["estado"]) for r in remitos] == [
        ("ENVIO", "RECIBIDO"),
        ("RETORNO", "GENERADO"),
    ]
    vuelta = cliente.get(f"{API}/remitos/{remitos[1]['id']}", headers=mundo["h_b"]).json()
    assert (vuelta["sede_origen_id"], vuelta["sede_destino_id"]) == (
        mundo["b"]["id"],
        mundo["a"]["id"],
    )
    _avanzar(cliente, mundo["h_b"], vuelta, "empaquetar", "despachar", "en-transito")
    _recibir(cliente, mundo["h_a"], vuelta, (ej["id"], "BUENO", {}))
    en_casa = _estado_ejemplar(cliente, mundo, ej)
    assert (en_casa["estado"], en_casa["sede_actual_id"]) == ("DISPONIBLE", mundo["a"]["id"])


# --- reglas del remito -----------------------------------------------------------------------


@pytest.mark.ca("CA-REM-12", "CA-REM-13", "CA-REM-11")
def test_reglas_al_generar_un_remito(cliente, mundo, sesion):
    ej = mundo["ej_a"][0]
    _remito(cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO")

    _error(
        _remito(cliente, mundo["h_a"], mundo["c"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO"),
        409,
        "EJEMPLAR_EN_OTRO_REMITO",
    )
    _error(
        _remito(
            cliente,
            mundo["h_a"],
            mundo["c"],
            [{"ejemplar_id": mundo["ej_b"][0]["id"]}],
            motivo="TRASLADO",
        ),
        422,
        "EJEMPLAR_FUERA_DE_SEDE_ORIGEN",
    )
    c = mundo["c"]
    baja = cliente.post(
        f"{API}/sedes/{c['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": c["version"]},
        headers=mundo["h_admin"],
    )
    assert baja.status_code == 200, baja.json()
    _error(
        _remito(
            cliente, mundo["h_a"], c, [{"ejemplar_id": mundo["ej_a"][1]["id"]}], motivo="TRASLADO"
        ),
        409,
        "SEDE_EN_BAJA",
    )


@pytest.mark.ca("CA-REM-15", "CA-REM-14")
def test_anular_libera_ejemplares_y_cancela_prestamos_solo_antes_de_despachar(cliente, mundo):
    ej, otro = mundo["ej_a"][0], mundo["ej_a"][1]
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej).json()
    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"], "prestamo_id": p["id"]}]
    ).json()
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar")

    anulado = cliente.post(
        f"{API}/remitos/{remito['id']}/anular",
        json={"motivo": "El socio desistió"},
        headers=mundo["h_a"],
    ).json()

    assert anulado["estado"] == "ANULADO"
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "DISPONIBLE"
    assert cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()["estado"] == (
        "CANCELADO"
    )
    despachado = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": otro["id"]}], motivo="TRASLADO"
    ).json()
    _avanzar(cliente, mundo["h_a"], despachado, "empaquetar", "despachar")
    _error(
        cliente.post(
            f"{API}/remitos/{despachado['id']}/anular",
            json={"motivo": "Ya no hace falta"},
            headers=mundo["h_a"],
        ),
        409,
        "TRANSICION_INVALIDA",
    )


@pytest.mark.ca("CA-REM-19", "CA-CAT-12")
def test_un_traslado_recibido_cambia_la_sede_propietaria(cliente, mundo):
    ej = mundo["ej_a"][0]
    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO"
    ).json()
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "APARTADO"
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar", "despachar")

    _recibir(cliente, mundo["h_b"], remito, (ej["id"], "REGULAR", {}))

    trasladado = _estado_ejemplar(cliente, mundo, ej)
    assert (trasladado["sede_propietaria_id"], trasladado["sede_actual_id"]) == (
        mundo["b"]["id"],
        mundo["b"]["id"],
    )
    assert (trasladado["estado"], trasladado["estado_fisico"]) == ("DISPONIBLE", "REGULAR")


@pytest.mark.ca("CA-REM-18")
def test_recepcion_con_dano_y_destruccion_registra_incidencias(cliente, mundo):
    ej1, ej2 = mundo["ej_a"][0], mundo["ej_a"][1]
    p1 = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej1).json()
    p2 = _prestar(cliente, mundo["h_b"], mundo["juan"], ej2).json()
    remito = _remito(
        cliente,
        mundo["h_a"],
        mundo["b"],
        [
            {"ejemplar_id": ej1["id"], "prestamo_id": p1["id"]},
            {"ejemplar_id": ej2["id"], "prestamo_id": p2["id"]},
        ],
    ).json()
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar", "despachar")

    _error(
        _recibir(
            cliente, mundo["h_b"], remito, (ej1["id"], "DANADO", {}), (ej2["id"], "BUENO", {})
        ),
        422,
        "REMITO_INVALIDO",
    )
    r = _recibir(
        cliente,
        mundo["h_b"],
        remito,
        (ej1["id"], "DANADO", {"observacion": "Tapa rota"}),
        (ej2["id"], "BUENO", {"destruido": True, "observacion": "Mojado, ilegible"}),
    )

    assert r.json()["estado"] == "DESTRUIDO"
    assert sorted(i["tipo"] for i in r.json()["incidencias"]) == ["DANIO", "DESTRUCCION"]
    # El dañado no queda en revisión en B (no es suya): espera el retorno a A.
    assert _estado_ejemplar(cliente, mundo, ej1)["estado"] == "APARTADO"
    assert _estado_ejemplar(cliente, mundo, ej2)["estado"] == "BAJA"
    for p in (p1, p2):
        estado = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()["estado"]
        assert estado == "CANCELADO"


@pytest.mark.ca("CA-REM-20", "CA-CAT-14")
def test_un_envio_danado_vuelve_a_su_sede_y_alli_se_revisa(cliente, mundo):
    ej = mundo["ej_a"][0]
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], ej).json()
    ida = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"], "prestamo_id": p["id"]}]
    ).json()
    _avanzar(cliente, mundo["h_a"], ida, "empaquetar", "despachar")
    _recibir(cliente, mundo["h_b"], ida, (ej["id"], "DANADO", {"observacion": "Tapa rota"}))

    en_b = _estado_ejemplar(cliente, mundo, ej)
    assert (en_b["estado"], en_b["estado_fisico"], en_b["sede_actual_id"]) == (
        "APARTADO",
        "DANADO",
        mundo["b"]["id"],
    )
    prestamo = cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()
    assert prestamo["estado"] == "CANCELADO"
    assert [(r["motivo"], r["estado"]) for r in prestamo["remitos"]] == [
        ("ENVIO", "DANADO"),
        ("RETORNO", "GENERADO"),
    ]
    vuelta = cliente.get(
        f"{API}/remitos/{prestamo['remitos'][1]['id']}", headers=mundo["h_b"]
    ).json()
    assert (vuelta["sede_origen_id"], vuelta["sede_destino_id"]) == (
        mundo["b"]["id"],
        mundo["a"]["id"],
    )

    _avanzar(cliente, mundo["h_b"], vuelta, "empaquetar", "despachar")
    r = _recibir(
        cliente,
        mundo["h_a"],
        vuelta,
        (ej["id"], "DANADO", {"observacion": "Sigue con la tapa rota"}),
    )
    assert r.json()["incidencias"] == []  # el daño ya se registró en el envío
    en_a = _estado_ejemplar(cliente, mundo, ej)
    assert (en_a["estado"], en_a["sede_actual_id"]) == ("EN_REVISION", mundo["a"]["id"])

    reparado = cliente.post(
        f"{API}/ejemplares/{ej['id']}/reparado",
        json={"version": en_a["version"]},
        headers=mundo["h_a"],
    ).json()
    assert (reparado["estado"], reparado["sede_actual_id"]) == ("DISPONIBLE", mundo["a"]["id"])

    llegadas = [m for m in en_a["historial"] if m["tipo"] == "CAMBIO_DE_UBICACION"]
    nombre_a, nombre_b = mundo["a"]["nombre"], mundo["b"]["nombre"]
    assert [m["cambios"] for m in llegadas] == [
        [
            {"campo": "sede_actual", "antes": nombre_a, "despues": nombre_b},
            {"campo": "estado_fisico", "antes": "BUENO", "despues": "DANADO"},
        ],
        [{"campo": "sede_actual", "antes": nombre_b, "despues": nombre_a}],
    ]


@pytest.mark.ca("CA-REM-21", "CA-CAT-14")
def test_un_traslado_danado_queda_en_revision_en_la_nueva_sede_propietaria(cliente, mundo):
    ej = mundo["ej_a"][0]
    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO"
    ).json()
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar", "despachar")

    _recibir(cliente, mundo["h_b"], remito, (ej["id"], "DANADO", {"observacion": "Mojado"}))

    e = _estado_ejemplar(cliente, mundo, ej)
    assert (e["estado"], e["sede_propietaria_id"], e["sede_actual_id"]) == (
        "EN_REVISION",
        mundo["b"]["id"],
        mundo["b"]["id"],
    )
    assert [m["tipo"] for m in e["historial"]][-2:] == ["TRASLADO", "CAMBIO_DE_ESTADO"]
    reparado = cliente.post(
        f"{API}/ejemplares/{ej['id']}/reparado",
        json={"version": e["version"]},
        headers=mundo["h_b"],
    )
    assert reparado.json()["estado"] == "DISPONIBLE"


@pytest.mark.ca("CA-REM-16", "CA-REM-17")
def test_extraviado_despues_del_plazo_da_de_baja_los_ejemplares(cliente, mundo, sesion):
    ej = mundo["ej_a"][0]
    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO"
    ).json()
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar", "despachar")
    ruta = f"{API}/remitos/{remito['id']}/extraviado"

    _error(
        cliente.post(ruta, json={"motivo": "No llegó a destino"}, headers=mundo["h_b"]),
        409,
        "PLAZO_DE_TRANSITO_VIGENTE",
    )
    sesion.execute(
        text("UPDATE remito SET fecha_despacho = now() - interval '8 days' WHERE id = :id"),
        {"id": remito["id"]},
    )
    sesion.commit()
    r = cliente.post(ruta, json={"motivo": "No llegó a destino"}, headers=mundo["h_admin"])

    assert r.json()["estado"] == "EXTRAVIADO"
    assert _estado_ejemplar(cliente, mundo, ej)["estado"] == "BAJA"
    traza = cliente.get(f"{API}/remitos/{remito['id']}", headers=mundo["h_admin"]).json()
    assert [i["tipo"] for i in traza["incidencias"]] == ["EXTRAVIO"]


# --- vencimientos, renovación y efectos en socios y sedes -----------------------------------


@pytest.mark.ca("CA-PRE-13", "CA-SOC-05")
def test_la_deteccion_de_vencidos_inhabilita_al_socio(cliente, mundo, sesion):
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"])
    sesion.execute(
        text("UPDATE prestamo SET fecha_vencimiento = :f WHERE id = :id"),
        {"f": HOY - timedelta(days=1), "id": p["id"]},
    )
    sesion.commit()

    _error(
        cliente.post(f"{API}/admin/tareas/detectar-vencidos", headers=mundo["h_b"]),
        403,
        "FORBIDDEN",
    )
    r = cliente.post(f"{API}/admin/tareas/detectar-vencidos", headers=mundo["h_admin"])

    assert r.json() == {"tarea": "detectar-vencidos", "cambios": 1}
    assert cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_b"]).json()["estado"] == (
        "VENCIDO"
    )
    ficha = cliente.get(f"{API}/socios/{mundo['lucia']['id']}", headers=mundo["h_b"]).json()
    assert (ficha["estado"], ficha["motivo_inhabilitacion"]) == ("INHABILITADO", "PRESTAMO_VENCIDO")
    assert ficha["situacion"]["prestamos_vencidos"] == 1
    _error(
        cliente.post(f"{API}/prestamos/{p['id']}/renovar", headers=mundo["h_b"]),
        409,
        "TRANSICION_INVALIDA",
    )


def test_renovar_extiende_el_vencimiento_una_vez(cliente, mundo):
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"])

    r = cliente.post(f"{API}/prestamos/{p['id']}/renovar", headers=mundo["h_b"]).json()

    assert (r["renovaciones"], r["fecha_vencimiento"]) == (1, str(HOY + timedelta(days=28)))
    _error(
        cliente.post(f"{API}/prestamos/{p['id']}/renovar", headers=mundo["h_b"]),
        409,
        "RENOVACION_NO_PERMITIDA",
    )


@pytest.mark.ca("CA-SED-05", "CA-SED-06", "CA-SED-20", "CA-SOC-09")
def test_prestamos_y_remitos_abiertos_bloquean_bajas(cliente, mundo):
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_a"][0]).json()
    _remito(
        cliente,
        mundo["h_a"],
        mundo["b"],
        [{"ejemplar_id": mundo["ej_a"][0]["id"], "prestamo_id": p["id"]}],
    )
    b = cliente.get(f"{API}/sedes/{mundo['b']['id']}", headers=mundo["h_admin"]).json()

    baja = cliente.post(
        f"{API}/sedes/{b['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": b["version"]},
        headers=mundo["h_admin"],
    )
    socio = cliente.post(
        f"{API}/socios/{mundo['lucia']['id']}/baja",
        json={"tipo": "A_PEDIDO", "motivo": "Se mudó"},
        headers=mundo["h_admin"],
    )

    tipos = {d["tipo"] for d in _error(baja, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")["detalles"]}
    assert {"PRESTAMOS_EN_CURSO", "REMITOS_ABIERTOS"} <= tipos
    _error(socio, 409, "SOCIO_CON_ACTIVIDAD_PENDIENTE")


def test_el_bibliotecario_no_ve_prestamos_ajenos_a_su_sede(
    cliente, mundo, crear_usuario, autenticar
):
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    h_c = autenticar(crear_usuario("BIBLIOTECARIO", sede_id=mundo["c"]["id"]))

    _error(cliente.get(f"{API}/prestamos/{p['id']}", headers=h_c), 404, "PRESTAMO_NO_ENCONTRADO")
    assert cliente.get(f"{API}/prestamos", headers=h_c).json()["total"] == 0
    _error(
        cliente.get(f"{API}/prestamos/{p['id']}", headers=mundo["h_a"]),
        404,
        "PRESTAMO_NO_ENCONTRADO",
    )


def test_parametros_los_cambia_solo_el_administrador(cliente, mundo):
    lista = cliente.get(f"{API}/parametros", headers=mundo["h_admin"]).json()
    assert {"clave": "plazo_prestamo_local_dias", "valor": "14"} == {
        k: v
        for k, v in lista[[x["clave"] for x in lista].index("plazo_prestamo_local_dias")].items()
        if k != "descripcion"
    }

    r = cliente.put(
        f"{API}/parametros/plazo_prestamo_local_dias",
        json={"valor": "10"},
        headers=mundo["h_admin"],
    )
    assert r.json()["valor"] == "10"
    _error(
        cliente.put(
            f"{API}/parametros/plazo_prestamo_local_dias",
            json={"valor": "-1"},
            headers=mundo["h_admin"],
        ),
        422,
        "VALIDACION",
    )
    _error(cliente.get(f"{API}/parametros", headers=mundo["h_b"]), 403, "FORBIDDEN")
    p = _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][0]).json()
    entregado = cliente.post(f"{API}/prestamos/{p['id']}/entregar", headers=mundo["h_b"]).json()
    assert entregado["fecha_vencimiento"] == str(HOY + timedelta(days=10))
