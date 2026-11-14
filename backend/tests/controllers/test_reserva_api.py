"""Reservas y la cola FIFO de punta a punta contra PostgreSQL."""

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

API = "/api/v1"


def _reservar(cliente, headers, m, socio=None, libro=0, sede="b"):
    cuerpo = {"libro_id": m["libros"][libro]["id"], "sede_retiro_id": m[sede]["id"]}
    if socio is not None:
        cuerpo["socio_id"] = socio["id"]
    return cliente.post(f"{API}/reservas", json=cuerpo, headers=headers)


@pytest.fixture
def ocupado(cliente, mundo):  # noqa: F811
    """El libro 0 sin disponibles en la red: B-0 apartado por un préstamo de Juan (el que
    devuelve) y A-0 por el de otro socio."""
    otro = _socio(cliente, mundo, "50999000", "Ocupante")
    assert _prestar(cliente, mundo["h_a"], otro, mundo["ej_a"][0]).status_code == 201
    return _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][0]).json()


def _agotar(cliente, m, libro):
    """Aparta todos los ejemplares del libro con préstamos de socios nuevos."""
    ejemplares = [(m["h_a"], m["ej_a"][libro])]
    if libro < len(m["ej_b"]):
        ejemplares.append((m["h_b"], m["ej_b"][libro]))
    for i, (headers, ejemplar) in enumerate(ejemplares):
        socio = _socio(cliente, m, f"5098{libro}{i:03d}", f"Lector {libro}{i}")
        assert _prestar(cliente, headers, socio, ejemplar).status_code == 201


def _socio(cliente, m, documento, nombre):
    return cliente.post(
        f"{API}/socios",
        json={
            "tipo_documento": "DNI",
            "nro_documento": documento,
            "nombre": nombre,
            "apellido": "Lector",
            "email": f"{documento}@example.com",
        },
        headers=m["h_b"],
    ).json()


# --- reservar --------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-01")
def test_con_ejemplares_disponibles_en_la_sede_corresponde_un_prestamo(cliente, mundo):  # noqa: F811
    _error(_reservar(cliente, mundo["h_lucia"], mundo), 409, "HAY_EJEMPLARES_DISPONIBLES")


@pytest.mark.ca("CA-RES-13")
def test_el_socio_reserva_para_si_y_ve_su_posicion(cliente, mundo, ocupado):  # noqa: F811
    r = _reservar(cliente, mundo["h_lucia"], mundo)

    assert r.status_code == 201, r.json()
    reserva = r.json()
    assert (reserva["estado"], reserva["socio_id"], reserva["posicion_en_cola"]) == (
        "PENDIENTE",
        mundo["lucia"]["id"],
        1,
    )
    assert reserva["numero"].startswith(f"RS-{HOY.year}-")
    otro = _socio(cliente, mundo, "50111222", "Otro")
    _reservar(cliente, mundo["h_b"], mundo, socio=otro)
    propias = cliente.get(f"{API}/reservas", headers=mundo["h_lucia"]).json()["items"]
    assert [x["id"] for x in propias] == [reserva["id"]]
    _error(
        cliente.get(f"{API}/reservas/{reserva['id'] + 1}", headers=mundo["h_lucia"]),
        404,
        "RESERVA_NO_ENCONTRADA",
    )


@pytest.mark.ca("CA-RES-02", "CA-RES-03", "CA-RES-04", "CA-RES-05")
def test_reglas_al_reservar(cliente, mundo, ocupado):  # noqa: F811
    _reservar(cliente, mundo["h_lucia"], mundo)
    _error(_reservar(cliente, mundo["h_lucia"], mundo), 409, "RESERVA_DUPLICADA")
    for i in (1, 2, 3):
        _agotar(cliente, mundo, i)
    for i in (1, 2):  # completa tres reservas activas con libros sin disponibles en la red
        assert _reservar(cliente, mundo["h_lucia"], mundo, libro=i, sede="c").status_code == 201
    _error(_reservar(cliente, mundo["h_lucia"], mundo, libro=3, sede="c"), 409, "LIMITE_RESERVAS")

    cliente.post(
        f"{API}/socios/{mundo['juan']['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )
    _error(
        _reservar(cliente, mundo["h_b"], mundo, socio=mundo["juan"], libro=4, sede="c"),
        409,
        "SOCIO_INHABILITADO",
    )
    c = cliente.get(f"{API}/sedes/{mundo['c']['id']}", headers=mundo["h_admin"]).json()
    otro = _socio(cliente, mundo, "50111222", "Otro")
    reservas_c = cliente.get(
        f"{API}/reservas", params={"socio_id": mundo["lucia"]["id"]}, headers=mundo["h_admin"]
    ).json()["items"]
    for r in reservas_c:
        cliente.post(f"{API}/reservas/{r['id']}/cancelar", headers=mundo["h_lucia"])
    baja = cliente.post(
        f"{API}/sedes/{c['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": c["version"]},
        headers=mundo["h_admin"],
    )
    assert baja.status_code == 200, baja.json()
    _error(
        _reservar(cliente, mundo["h_b"], mundo, socio=otro, libro=4, sede="c"), 409, "SEDE_EN_BAJA"
    )


# --- cola ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-06", "CA-RES-07", "CA-RES-08", "CA-RES-12")
def test_el_ejemplar_liberado_va_al_primero_elegible_de_la_cola(cliente, mundo, ocupado):  # noqa: F811
    inhabilitada = _socio(cliente, mundo, "50111111", "Primera")
    segunda = _socio(cliente, mundo, "50222222", "Segunda")
    tercera = _socio(cliente, mundo, "50333333", "Tercera")
    ids = [
        _reservar(cliente, mundo["h_b"], mundo, socio=s).json()["id"]
        for s in (inhabilitada, segunda, tercera)
    ]
    cliente.post(
        f"{API}/socios/{inhabilitada['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )

    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])

    estados = [cliente.get(f"{API}/reservas/{i}", headers=mundo["h_b"]).json() for i in ids]
    assert [e["estado"] for e in estados] == ["PENDIENTE", "DISPONIBLE_PARA_RETIRO", "PENDIENTE"]
    assert estados[1]["vencimiento_retiro"] == str(HOY + timedelta(days=3))
    assert estados[1]["codigo_ejemplar"] == "B-0"
    assert [estados[0]["posicion_en_cola"], estados[2]["posicion_en_cola"]] == [1, 2]
    ejemplar = cliente.get(
        f"{API}/ejemplares/{mundo['ej_b'][0]['id']}", headers=mundo["h_b"]
    ).json()
    assert ejemplar["estado"] == "RESERVADO"

    prestamo = cliente.post(f"{API}/reservas/{ids[1]}/retirar", headers=mundo["h_b"]).json()
    assert (prestamo["estado"], prestamo["socio_id"], prestamo["tipo"]) == (
        "ACTIVO",
        segunda["id"],
        "LOCAL",
    )
    assert prestamo["fecha_vencimiento"] == str(HOY + timedelta(days=14))
    cumplida = cliente.get(f"{API}/reservas/{ids[1]}", headers=mundo["h_b"]).json()
    assert (cumplida["estado"], cumplida["prestamo_id"]) == ("CUMPLIDA", prestamo["id"])
    _error(
        cliente.post(f"{API}/reservas/{ids[1]}/cancelar", headers=mundo["h_b"]),
        409,
        "TRANSICION_INVALIDA",
    )


@pytest.mark.ca("CA-RES-10")
def test_una_reserva_no_retirada_vence_y_pasa_a_la_siguiente(cliente, mundo, ocupado, sesion):  # noqa: F811
    primera = _reservar(cliente, mundo["h_lucia"], mundo).json()
    otro = _socio(cliente, mundo, "50111222", "Otro")
    segunda = _reservar(cliente, mundo["h_b"], mundo, socio=otro).json()
    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])
    sesion.execute(
        text("UPDATE reserva SET vencimiento_retiro = :f WHERE id = :id"),
        {"f": HOY - timedelta(days=1), "id": primera["id"]},
    )
    sesion.commit()

    r = cliente.post(f"{API}/admin/tareas/vencer-reservas", headers=mundo["h_admin"])

    assert r.json() == {"tarea": "vencer-reservas", "cambios": 1}
    estados = [
        cliente.get(f"{API}/reservas/{x['id']}", headers=mundo["h_b"]).json()["estado"]
        for x in (primera, segunda)
    ]
    assert estados == ["VENCIDA", "DISPONIBLE_PARA_RETIRO"]


@pytest.mark.ca("CA-RES-09")
def test_un_ejemplar_liberado_en_otra_sede_inicia_un_prestamo_entre_sedes(cliente, mundo):  # noqa: F811
    prestamo_a = _prestar(cliente, mundo["h_a"], mundo["juan"], mundo["ej_a"][4]).json()
    reserva = _reservar(cliente, mundo["h_lucia"], mundo, libro=4).json()

    cliente.post(f"{API}/prestamos/{prestamo_a['id']}/cancelar", json={}, headers=mundo["h_a"])

    cumplida = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_lucia"]).json()
    assert cumplida["estado"] == "CUMPLIDA"
    nuevo = cliente.get(f"{API}/prestamos/{cumplida['prestamo_id']}", headers=mundo["h_b"]).json()
    assert (nuevo["tipo"], nuevo["estado"], nuevo["sede_origen_id"], nuevo["sede_destino_id"]) == (
        "INTERBIBLIOTECARIO",
        "SOLICITADO",
        mundo["a"]["id"],
        mundo["b"]["id"],
    )
    assert nuevo["socio_id"] == mundo["lucia"]["id"]


@pytest.mark.ca("CA-PRE-17", "CA-SED-19")
def test_las_reservas_impiden_renovar_y_dar_de_baja_la_sede(cliente, mundo, ocupado):  # noqa: F811
    cliente.post(f"{API}/prestamos/{ocupado['id']}/entregar", headers=mundo["h_b"])
    _reservar(cliente, mundo["h_lucia"], mundo, sede="c")

    _error(
        cliente.post(f"{API}/prestamos/{ocupado['id']}/renovar", headers=mundo["h_b"]),
        409,
        "RENOVACION_NO_PERMITIDA",
    )
    c = cliente.get(f"{API}/sedes/{mundo['c']['id']}", headers=mundo["h_admin"]).json()
    baja = cliente.post(
        f"{API}/sedes/{c['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": c["version"]},
        headers=mundo["h_admin"],
    )
    tipos = [d["tipo"] for d in _error(baja, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")["detalles"]]
    assert tipos == ["RESERVAS_PENDIENTES"]


def test_la_baja_del_socio_cancela_sus_reservas(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_lucia"], mundo).json()
    ficha = cliente.get(f"{API}/socios/{mundo['lucia']['id']}", headers=mundo["h_b"]).json()
    assert ficha["situacion"]["reservas_activas"] == 1

    baja = cliente.post(
        f"{API}/socios/{mundo['lucia']['id']}/baja",
        json={"tipo": "A_PEDIDO", "motivo": "Se mudó"},
        headers=mundo["h_admin"],
    )

    assert baja.json()["estado"] == "BAJA" and baja.json()["reservas_canceladas"] == 1
    assert (
        cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_b"]).json()["estado"]
        == "CANCELADA"
    )


# --- disponibilidad en la red y alta de ejemplares --------------------------------------------


@pytest.mark.ca("CA-RES-14")
def test_con_disponibles_en_otra_sede_corresponde_un_prestamo_entre_sedes(cliente, mundo):  # noqa: F811
    # El libro 2 solo está en A, disponible: Lucía quiere retirarlo en C.
    error = _error(
        _reservar(cliente, mundo["h_lucia"], mundo, libro=2, sede="c"),
        409,
        "HAY_EJEMPLARES_DISPONIBLES",
    )

    assert error["detalles"][0]["problema"] == "disponibles_en_otra_sede"
    assert error["detalles"][0]["sedes"] == [mundo["a"]["id"]]
    assert "préstamo entre sedes" in error["mensaje"]


@pytest.mark.ca("CA-RES-14")
def test_un_libro_sin_ejemplares_en_la_red_no_se_reserva(cliente, mundo, sesion):  # noqa: F811
    categoria = mundo["libros"][0]["categoria"]["id"]
    libro = cliente.post(
        f"{API}/libros",
        json={"titulo": "Sin ejemplares", "autores": ["Nadie"], "categoria_id": categoria},
        headers=mundo["h_admin"],
    ).json()
    cuerpo = {"libro_id": libro["id"], "sede_retiro_id": mundo["b"]["id"]}

    _error(
        cliente.post(f"{API}/reservas", json=cuerpo, headers=mundo["h_lucia"]),
        409,
        "LIBRO_SIN_EJEMPLARES",
    )


@pytest.mark.ca("CA-RES-15")
def test_un_ejemplar_nuevo_se_asigna_a_la_cola(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_lucia"], mundo).json()  # libro 0, retiro en B

    nuevo = cliente.post(
        f"{API}/ejemplares",
        json={
            "libro_id": mundo["libros"][0]["id"],
            "codigo_inventario": "B-0-NUEVO",
            "sede_id": mundo["b"]["id"],
        },
        headers=mundo["h_admin"],
    )

    assert nuevo.status_code == 201, nuevo.json()
    assert nuevo.json()["estado"] == "RESERVADO"
    asignada = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_lucia"]).json()
    assert (asignada["estado"], asignada["codigo_ejemplar"]) == (
        "DISPONIBLE_PARA_RETIRO",
        "B-0-NUEVO",
    )


# --- autoría, permisos e historial ------------------------------------------------------------


@pytest.mark.ca("CA-RES-16")
def test_la_reasignacion_la_hace_el_sistema_y_no_quien_libero(cliente, mundo, ocupado):  # noqa: F811
    lucia = _reservar(cliente, mundo["h_lucia"], mundo).json()  # retiro en B
    otro = _socio(cliente, mundo, "50111222", "Otro")
    de_otro = _reservar(cliente, mundo["h_b"], mundo, socio=otro, sede="c").json()
    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])

    # Lucía cancela la suya ya asignada: el ejemplar pasa a Otro con un préstamo entre sedes.
    cliente.post(f"{API}/reservas/{lucia['id']}/cancelar", headers=mundo["h_lucia"])

    cumplida = cliente.get(f"{API}/reservas/{de_otro['id']}", headers=mundo["h_b"]).json()
    assert cumplida["estado"] == "CUMPLIDA"
    assert [(m["estado_nuevo"], m["autor"]) for m in cumplida["historial"]] == [
        ("PENDIENTE", "Beto B"),
        ("CUMPLIDA", "Sistema"),
    ]
    prestamo = cliente.get(
        f"{API}/prestamos/{cumplida['prestamo_id']}", headers=mundo["h_b"]
    ).json()
    assert prestamo["registrado_por"] is None
    assert prestamo["historial"][0]["autor"] == "Sistema"
    propia = cliente.get(f"{API}/reservas/{lucia['id']}", headers=mundo["h_lucia"]).json()
    assert [(m["estado_nuevo"], m["autor"]) for m in propia["historial"]] == [
        ("PENDIENTE", "Vos"),
        ("DISPONIBLE_PARA_RETIRO", "Sistema"),
        ("CANCELADA", "Vos"),
    ]


@pytest.mark.ca("CA-RES-17")
def test_cancela_el_socio_o_el_bibliotecario_de_la_sede_de_retiro(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_lucia"], mundo).json()  # retiro en B
    otro = _socio(cliente, mundo, "50111222", "Otro")
    ajena = _reservar(cliente, mundo["h_b"], mundo, socio=otro).json()
    url = f"{API}/reservas/{reserva['id']}/cancelar"

    _error(cliente.post(url, headers=mundo["h_admin"]), 403, "FORBIDDEN")
    _error(cliente.post(url, headers=mundo["h_a"]), 403, "FORBIDDEN")
    _error(  # un socio no ve ni cancela la de otro (CU-RES-05, A3)
        cliente.post(f"{API}/reservas/{ajena['id']}/cancelar", headers=mundo["h_lucia"]),
        404,
        "RESERVA_NO_ENCONTRADA",
    )
    r = cliente.post(
        url, json={"motivo": "El socio avisó que ya no lo necesita"}, headers=mundo["h_b"]
    )

    assert r.status_code == 200, r.json()
    assert r.json()["estado"] == "CANCELADA"
    historial = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_b"]).json()
    assert historial["historial"][-1]["observacion"] == "El socio avisó que ya no lo necesita"


@pytest.mark.ca("CA-RES-18")
def test_el_socio_no_reserva_a_nombre_de_otro(cliente, mundo, ocupado):  # noqa: F811
    _error(
        _reservar(cliente, mundo["h_lucia"], mundo, socio=mundo["juan"]),
        403,
        "FORBIDDEN",
    )
    propia = _reservar(cliente, mundo["h_lucia"], mundo, socio=mundo["lucia"])

    assert propia.status_code == 201
    assert propia.json()["socio_id"] == mundo["lucia"]["id"]


@pytest.mark.ca("CA-RES-19")
def test_la_reserva_guarda_quien_la_registro_y_su_historial(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_b"], mundo, socio=mundo["lucia"]).json()
    assert reserva["registrada_por"]["nombre"] == "Beto B"

    cliente.post(
        f"{API}/reservas/{reserva['id']}/cancelar",
        json={"motivo": "Ya lo conseguí"},
        headers=mundo["h_lucia"],
    )

    personal = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_b"]).json()
    assert personal["registrada_por"]["nombre"] == "Beto B"
    assert [
        (m["estado_anterior"], m["estado_nuevo"], m["autor"]) for m in personal["historial"]
    ] == [
        (None, "PENDIENTE", "Beto B"),
        ("PENDIENTE", "CANCELADA", "Lucía Socio"),
    ]
    propia = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_lucia"]).json()
    assert "registrada_por" not in propia
    assert [(m["autor"], m["usuario"], m["observacion"]) for m in propia["historial"]] == [
        ("Personal de la biblioteca", None, "Reserva registrada"),
        ("Vos", None, "Ya lo conseguí"),
    ]
    assert propia["fecha_cierre"] is not None


# --- cola -------------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-20")
def test_la_asignacion_saltea_al_socio_que_no_puede_retirarlo(cliente, mundo, ocupado, sesion):  # noqa: F811
    sesion.execute(
        text("UPDATE parametro SET valor = '1' WHERE clave = 'prestamos_maximos_por_socio'")
    )
    sesion.commit()
    assert _prestar(cliente, mundo["h_b"], mundo["lucia"], mundo["ej_b"][1]).status_code == 201
    lucia = _reservar(cliente, mundo["h_lucia"], mundo).json()  # primera, pero sin cupo
    otro = _socio(cliente, mundo, "50111222", "Otro")
    de_otro = _reservar(cliente, mundo["h_b"], mundo, socio=otro).json()

    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])

    estados = [
        cliente.get(f"{API}/reservas/{r['id']}", headers=mundo["h_b"]).json()
        for r in (lucia, de_otro)
    ]
    assert [(e["estado"], e["posicion_en_cola"]) for e in estados] == [
        ("PENDIENTE", 1),
        ("DISPONIBLE_PARA_RETIRO", None),
    ]


@pytest.mark.ca("CA-RES-21")
def test_sin_ejemplares_en_la_red_las_reservas_pendientes_se_cancelan(cliente, mundo, sesion):  # noqa: F811
    ej = mundo["ej_a"][4]  # único ejemplar del libro 4
    prestamo = _entregado(cliente, sesion, mundo["h_a"], mundo["juan"], ej)
    reserva = _reservar(cliente, mundo["h_lucia"], mundo, libro=4).json()
    devuelto = _devolver(cliente, mundo["h_a"], prestamo, "DANADO", observaciones="Hojas sueltas")
    assert devuelto.status_code == 201, devuelto.json()
    assert _reserva(cliente, mundo, reserva)["estado"] == "PENDIENTE"  # en revisión: puede volver

    actual = cliente.get(f"{API}/ejemplares/{ej['id']}", headers=mundo["h_a"]).json()
    baja = cliente.post(
        f"{API}/ejemplares/{ej['id']}/baja",
        json={"motivo": "Irreparable", "version": actual["version"]},
        headers=mundo["h_a"],
    )

    assert baja.status_code == 200, baja.json()
    cancelada = _reserva(cliente, mundo, reserva)
    assert cancelada["estado"] == "CANCELADA"
    assert (cancelada["historial"][-1]["autor"], cancelada["historial"][-1]["observacion"]) == (
        "Sistema",
        "El libro ya no tiene ejemplares en la red",
    )


@pytest.mark.ca("CA-RES-21")
def test_el_ultimo_ejemplar_recibido_destruido_cancela_las_reservas(cliente, mundo):  # noqa: F811
    ej = mundo["ej_a"][4]  # único ejemplar del libro 4, trasladado de A a B
    remito = _remito(
        cliente, mundo["h_a"], mundo["b"], [{"ejemplar_id": ej["id"]}], motivo="TRASLADO"
    ).json()
    _avanzar(cliente, mundo["h_a"], remito, "empaquetar", "despachar")
    reserva = _reservar(cliente, mundo["h_lucia"], mundo, libro=4).json()  # en tránsito

    r = _recibir(
        cliente,
        mundo["h_b"],
        remito,
        (ej["id"], "DANADO", {"destruido": True, "observacion": "Mojado por la lluvia"}),
    )

    assert r.status_code == 200, r.json()
    cancelada = _reserva(cliente, mundo, reserva)
    assert cancelada["estado"] == "CANCELADA"
    assert cancelada["historial"][-1]["autor"] == "Sistema"


def _reserva(cliente, m, reserva):
    return cliente.get(f"{API}/reservas/{reserva['id']}", headers=m["h_b"]).json()


@pytest.mark.ca("CA-RES-22")
def test_cola_de_un_libro_en_orden_fifo_y_filtro_por_sede(cliente, mundo, ocupado):  # noqa: F811
    socios = [_socio(cliente, mundo, f"5011100{i}", f"Socio {i}") for i in range(3)]
    sedes = ["b", "c", "b"]
    ids = [
        _reservar(cliente, mundo["h_b"], mundo, socio=s, sede=sede).json()["id"]
        for s, sede in zip(socios, sedes, strict=True)
    ]
    base = {"libro_id": mundo["libros"][0]["id"], "estado": "PENDIENTE"}

    cola = cliente.get(
        f"{API}/reservas", params={**base, "orden": "cola"}, headers=mundo["h_b"]
    ).json()["items"]
    en_c = cliente.get(
        f"{API}/reservas", params={**base, "sede_retiro_id": mundo["c"]["id"]}, headers=mundo["h_b"]
    ).json()["items"]

    assert [(r["id"], r["posicion_en_cola"]) for r in cola] == [
        (ids[0], 1),
        (ids[1], 2),
        (ids[2], 3),
    ]
    assert [r["id"] for r in en_c] == [ids[1]]


# --- retiro -----------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-12")
def test_el_retiro_se_rechaza_en_otra_sede_o_con_el_socio_inhabilitado(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_lucia"], mundo).json()
    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])
    url = f"{API}/reservas/{reserva['id']}/retirar"

    _error(cliente.post(url, headers=mundo["h_a"]), 403, "FORBIDDEN")
    cliente.post(
        f"{API}/socios/{mundo['lucia']['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )
    _error(cliente.post(url, headers=mundo["h_b"]), 409, "SOCIO_INHABILITADO")
    assert _reserva(cliente, mundo, reserva)["estado"] == "DISPONIBLE_PARA_RETIRO"
