"""API de sedes: permisos por rol, forma de las respuestas y formato de errores."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.db.models import LocalidadORM
from app.utils.texto import normalizar

BASE = "/api/v1/sedes"


def _hoy() -> date:
    """Hoy en la zona de negocio (el CI corre en UTC: de 21 a 24 h ya sería mañana)."""
    return datetime.now(ZoneInfo("America/Argentina/Cordoba")).date()


@pytest.fixture
def localidad_id(sesion) -> int:
    return sesion.scalar(select(LocalidadORM.id).where(LocalidadORM.nombre == "Córdoba"))


@pytest.fixture
def admin(crear_usuario):
    return crear_usuario("ADMIN", nombre="Ana Admin")


@pytest.fixture
def h_admin(admin, autenticar):
    return autenticar(admin)


@pytest.fixture
def h_biblio(crear_usuario, autenticar, sesion, h_admin, cliente, localidad_id):
    sede_id = _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo="BASE_B",
        nombre="Sede de Bibliotecario",
        calle="Calle B",
        numero="1",
    ).json()["id"]
    return autenticar(crear_usuario("BIBLIOTECARIO", sede_id=sede_id))


@pytest.fixture
def h_socio(crear_usuario, autenticar, sesion, h_admin, cliente, localidad_id):
    sede_id = _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo="BASE_S",
        nombre="Sede de Socio",
        calle="Calle S",
        numero="2",
    ).json()["id"]

    socio = crear_usuario("SOCIO", socio_id=_crear_socio(sesion, sede_id))
    return autenticar(socio)


def _crear_socio(sesion, sede_id: int) -> int:
    from app.db.models import SocioORM

    socio = SocioORM(
        numero_socio=f"S{sede_id:06d}",
        tipo_documento="DNI",
        nro_documento=f"3000{sede_id:04d}",
        nombre="Soci",
        apellido="O",
        sede_alta_id=sede_id,
    )
    sesion.add(socio)
    sesion.flush()
    return socio.id


def cuerpo(localidad_id: int, **over) -> dict:
    datos = {
        "codigo": "norte",
        "nombre": "Sede Norte",
        "calle": "Av. Colón",
        "numero": "4500",
        "localidad_id": localidad_id,
        "telefono": "+54 351 400-0000",
        "email": "Norte@red.example",
        "responsable": "Ana Pérez",
        "horarios": [
            {"dia_semana": 1, "apertura": "09:00", "cierre": "13:00"},
            {"dia_semana": 1, "apertura": "15:00", "cierre": "19:00"},
            {"dia_semana": 2, "apertura": "09:00", "cierre": "18:00"},
        ],
    }
    datos.update(over)
    return datos


def _alta(cliente, headers, localidad_id, **over):
    return cliente.post(BASE, json=cuerpo(localidad_id, **over), headers=headers)


def _error(respuesta, estado: int, codigo: str) -> dict:
    assert respuesta.status_code == estado, respuesta.text
    error = respuesta.json()["error"]
    assert error["codigo"] == codigo
    assert isinstance(error["mensaje"], str) and isinstance(error["detalles"], list)
    return error


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-01", "CA-SED-26", "CA-SED-27", "CA-SED-28", "CA-SED-35")
def test_el_alta_responde_201_con_location_y_el_esquema_de_administrador(
    cliente, h_admin, localidad_id
):
    r = _alta(cliente, h_admin, localidad_id)

    assert r.status_code == 201
    sede = r.json()
    assert r.headers["location"] == f"{BASE}/{sede['id']}"
    assert (sede["codigo"], sede["estado"], sede["version"]) == ("NORTE", "ACTIVA", 1)
    assert sede["contacto"] == {
        "telefono": "+543514000000",
        "email": "norte@red.example",
        "responsable": "Ana Pérez",
    }
    assert (
        sede["direccion"]["localidad"] == "Córdoba" and sede["direccion"]["provincia"] == "Córdoba"
    )
    assert [(h["dia_semana"], h["apertura"]) for h in sede["horarios"]] == [
        (1, "09:00"),
        (1, "15:00"),
        (2, "09:00"),
    ]
    assert sede["baja"] is None and sede["creado_por"]["nombre"] == "Ana Admin"
    assert isinstance(sede["abierta_ahora"], bool) and sede["excepciones"] == []


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"codigo": "ab"}, "codigo"),
        ({"codigo": "CEN-1"}, "codigo"),
        ({"telefono": "351 400"}, "telefono"),
        ({"email": "sin-arroba"}, "email"),
        ({"numero": "abc"}, "numero"),
        ({"nombre": "  "}, "nombre"),
        ({"responsable": "A"}, "responsable"),
    ],
)
@pytest.mark.ca("CA-SED-26", "CA-SED-27", "CA-SED-28", "CA-SED-29")
def test_un_formato_invalido_responde_422_indicando_el_campo(
    cliente, h_admin, localidad_id, cambio, campo
):
    error = _error(_alta(cliente, h_admin, localidad_id, **cambio), 422, "VALIDACION")

    assert error["detalles"][0]["campo"] == campo


def test_faltan_campos_obligatorios(cliente, h_admin):
    r = cliente.post(BASE, json={"codigo": "NORTE"}, headers=h_admin)

    error = _error(r, 422, "VALIDACION")
    assert {"nombre", "calle", "localidad_id", "horarios"} <= {
        d["campo"] for d in error["detalles"]
    }


@pytest.mark.ca("CA-SED-38")
def test_localidad_fuera_del_catalogo(cliente, h_admin):
    _error(_alta(cliente, h_admin, 999_999), 422, "LOCALIDAD_INVALIDA")


@pytest.mark.ca("CA-SED-30", "CA-SED-31", "CA-SED-32")
@pytest.mark.parametrize(
    "horarios",
    [
        [],
        [
            {"dia_semana": 1, "apertura": "09:00", "cierre": "13:00"},
            {"dia_semana": 1, "apertura": "12:00", "cierre": "14:00"},
        ],
        [{"dia_semana": 1, "apertura": "13:00", "cierre": "09:00"}],
        [{"dia_semana": 8, "apertura": "09:00", "cierre": "13:00"}],
        [
            {"dia_semana": 1, "apertura": f"{9 + 2 * i:02d}:00", "cierre": f"{10 + 2 * i:02d}:00"}
            for i in range(5)
        ],
    ],
)
def test_horarios_invalidos(cliente, h_admin, localidad_id, horarios):
    error = _error(
        _alta(cliente, h_admin, localidad_id, horarios=horarios), 422, "HORARIO_INVALIDO"
    )

    assert error["detalles"][0]["campo"] == "horarios"


@pytest.mark.ca("CA-SED-02", "CA-SED-13")
def test_codigo_y_nombre_duplicados_responden_409_con_la_sede_existente(
    cliente, h_admin, localidad_id
):
    existente = _alta(cliente, h_admin, localidad_id).json()

    por_codigo = _alta(
        cliente, h_admin, localidad_id, codigo="NORTE", nombre="Otra", calle="Otra", numero="1"
    )
    por_nombre = _alta(
        cliente, h_admin, localidad_id, codigo="OTRA", nombre="SEDE NORTE", calle="Otra", numero="2"
    )

    e1 = _error(por_codigo, 409, "SEDE_CODIGO_DUPLICADO")
    e2 = _error(por_nombre, 409, "SEDE_NOMBRE_DUPLICADO")
    assert e1["detalles"][0]["sede"]["id"] == e2["detalles"][0]["sede"]["id"] == existente["id"]


@pytest.mark.ca("CA-SED-03", "CA-SED-04")
def test_direccion_repetida_se_advierte_y_se_puede_confirmar(cliente, h_admin, localidad_id):
    _alta(cliente, h_admin, localidad_id)
    repetida = {"codigo": "SUR", "nombre": "Sede Sur", "calle": "AVENIDA Colon", "numero": "04500"}

    error = _error(_alta(cliente, h_admin, localidad_id, **repetida), 409, "DIRECCION_DUPLICADA")
    assert error["detalles"][0]["campo"] == "direccion"
    assert error["detalles"][0]["sede"]["codigo"] == "NORTE"

    confirmada = _alta(
        cliente, h_admin, localidad_id, confirmar_direccion_duplicada=True, **repetida
    )
    assert confirmada.status_code == 201
    historial = cliente.get(f"{BASE}/{confirmada.json()['id']}/historial", headers=h_admin).json()
    assert "direccion_duplicada_confirmada" in {
        c["campo"] for c in historial["items"][0]["cambios"]
    }


# --- permisos --------------------------------------------------------------------------------

ADMIN_SOLO = [
    ("POST", BASE),
    ("GET", f"{BASE}/resumen"),
    ("PUT", f"{BASE}/{{id}}"),
    ("POST", f"{BASE}/{{id}}/baja"),
    ("POST", f"{BASE}/{{id}}/reactivar"),
    ("POST", f"{BASE}/{{id}}/excepciones-horario"),
    ("DELETE", f"{BASE}/{{id}}/excepciones-horario/1"),
    ("GET", f"{BASE}/{{id}}/historial"),
]
LECTURA = [
    ("GET", BASE),
    ("GET", f"{BASE}/{{id}}"),
    ("GET", f"{BASE}/{{id}}/excepciones-horario"),
    ("GET", "/api/v1/localidades"),
    ("GET", "/api/v1/provincias"),
]


@pytest.mark.ca("CA-SED-46")
@pytest.mark.parametrize(("metodo", "ruta"), ADMIN_SOLO + LECTURA)
def test_sin_token_todo_responde_401(cliente, metodo, ruta):
    r = cliente.request(metodo, ruta.format(id=1), json={})

    _error(r, 401, "TOKEN_INVALIDO")


@pytest.mark.ca("CA-SED-46")
@pytest.mark.parametrize(("metodo", "ruta"), ADMIN_SOLO)
@pytest.mark.parametrize("rol", ["h_biblio", "h_socio"])
def test_bibliotecario_y_socio_no_administran_sedes(
    cliente, h_admin, localidad_id, request, rol, metodo, ruta
):
    sede = _alta(cliente, h_admin, localidad_id).json()
    headers = request.getfixturevalue(rol)

    r = cliente.request(metodo, ruta.format(id=sede["id"]), json={}, headers=headers)

    _error(r, 403, "FORBIDDEN")


@pytest.mark.ca("CA-SED-46")
@pytest.mark.parametrize(("metodo", "ruta"), LECTURA)
@pytest.mark.parametrize("rol", ["h_admin", "h_biblio", "h_socio"])
def test_todos_los_roles_consultan(cliente, h_admin, localidad_id, request, rol, metodo, ruta):
    sede = _alta(cliente, h_admin, localidad_id).json()

    r = cliente.request(metodo, ruta.format(id=sede["id"]), headers=request.getfixturevalue(rol))

    assert r.status_code == 200


# --- visibilidad por rol ---------------------------------------------------------------------


@pytest.mark.ca("CA-SED-43", "CA-SED-44", "CA-SED-45")
def test_cada_rol_recibe_solo_los_campos_que_puede_ver(
    cliente, h_admin, h_biblio, h_socio, localidad_id
):
    sede_id = _alta(cliente, h_admin, localidad_id).json()["id"]

    admin = cliente.get(f"{BASE}/{sede_id}", headers=h_admin).json()
    biblio = cliente.get(f"{BASE}/{sede_id}", headers=h_biblio).json()
    socio = cliente.get(f"{BASE}/{sede_id}", headers=h_socio).json()

    assert {"baja", "version", "creado_por", "actualizado_en"} <= admin.keys()
    assert "estado" in biblio and "responsable" in biblio["contacto"]
    assert not {"baja", "version", "creado_por", "creado_en", "actualizado_por"} & biblio.keys()
    assert not {"estado", "baja", "version"} & socio.keys()
    assert set(socio["contacto"]) == {"telefono", "email"}
    assert {"horarios", "excepciones", "abierta_ahora", "direccion"} <= socio.keys()


@pytest.mark.ca("CA-SED-11", "CA-SED-45")
def test_un_socio_recibe_404_ante_una_sede_en_baja_y_no_la_ve_en_el_listado(
    cliente, h_admin, h_biblio, h_socio, localidad_id
):
    sede = _alta(cliente, h_admin, localidad_id).json()
    cliente.post(
        f"{BASE}/{sede['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    error = _error(cliente.get(f"{BASE}/{sede['id']}", headers=h_socio), 404, "SEDE_NO_ENCONTRADA")
    assert error["mensaje"] == "La sede solicitada no existe o no está disponible."
    assert cliente.get(f"{BASE}/{sede['id']}", headers=h_biblio).json()["estado"] == "BAJA"
    for estado in ("BAJA", "TODAS", "ACTIVA"):
        items = cliente.get(BASE, params={"estado": estado}, headers=h_socio).json()["items"]
        assert sede["id"] not in {s["id"] for s in items}
        assert all("estado" not in s for s in items)


def test_sede_inexistente_responde_404(cliente, h_admin):
    _error(cliente.get(f"{BASE}/999999", headers=h_admin), 404, "SEDE_NO_ENCONTRADA")


# --- listado ---------------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-43", "CA-SED-44")
def test_listado_filtra_pagina_y_ordena(cliente, h_admin, localidad_id):
    for codigo, nombre in [("AAA", "Alfa"), ("BBB", "Beta"), ("CCC", "Gamma")]:
        _alta(
            cliente, h_admin, localidad_id, codigo=codigo, nombre=nombre, calle=nombre, numero="1"
        )
    beta = cliente.get(BASE, params={"q": "beta"}, headers=h_admin).json()
    assert [s["codigo"] for s in beta["items"]] == ["BBB"]
    baja = cliente.get(BASE, params={"q": "gamma"}, headers=h_admin).json()["items"][0]
    cliente.post(
        f"{BASE}/{baja['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    todas = cliente.get(
        BASE, params={"q": "a", "orden": "-nombre", "size": 2}, headers=h_admin
    ).json()
    assert (todas["page"], todas["size"]) == (1, 2) and len(todas["items"]) == 2
    activas = cliente.get(
        BASE, params={"estado": "ACTIVA", "orden": "codigo"}, headers=h_admin
    ).json()
    assert "CCC" not in {s["codigo"] for s in activas["items"]}
    solo_baja = cliente.get(BASE, params={"estado": "BAJA"}, headers=h_admin).json()
    assert [s["codigo"] for s in solo_baja["items"]] == ["CCC"] and solo_baja["total"] == 1


def test_parametros_de_listado_invalidos(cliente, h_admin):
    for params in ({"page": 0}, {"size": 101}, {"estado": "X"}, {"orden": "id"}):
        _error(cliente.get(BASE, params=params, headers=h_admin), 422, "VALIDACION")


def test_el_bibliotecario_ve_activas_por_defecto(cliente, h_admin, h_biblio, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    cliente.post(
        f"{BASE}/{sede['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    por_defecto = cliente.get(BASE, headers=h_biblio).json()["items"]
    con_baja = cliente.get(BASE, params={"estado": "TODAS"}, headers=h_biblio).json()["items"]

    assert sede["id"] not in {s["id"] for s in por_defecto}
    assert sede["id"] in {s["id"] for s in con_baja}


def test_resumen(cliente, h_admin, localidad_id):
    antes = cliente.get(f"{BASE}/resumen", headers=h_admin).json()
    sede = _alta(cliente, h_admin, localidad_id).json()
    cliente.post(
        f"{BASE}/{sede['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    despues = cliente.get(f"{BASE}/resumen", headers=h_admin).json()

    assert despues == {
        "total": antes["total"] + 1,
        "activas": antes["activas"],
        "en_baja": antes["en_baja"] + 1,
    }


# --- modificación, baja y reactivación -------------------------------------------------------


def _modificacion(localidad_id, version, **over):
    datos = cuerpo(localidad_id, **over)
    datos.pop("codigo")
    return {"version": version, **datos}


@pytest.mark.ca("CA-SED-12", "CA-SED-14", "CA-SED-15", "CA-SED-35", "CA-SED-41")
def test_modificar_incrementa_la_version_y_controla_los_conflictos(cliente, h_admin, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    url = f"{BASE}/{sede['id']}"

    ok = cliente.put(
        url,
        json=_modificacion(localidad_id, 1, telefono="+543514999999", numero="4600"),
        headers=h_admin,
    )
    assert ok.status_code == 200 and ok.json()["version"] == 2
    assert ok.json()["contacto"]["telefono"] == "+543514999999"

    viejo = cliente.put(url, json=_modificacion(localidad_id, 1), headers=h_admin)
    error = _error(viejo, 409, "CONFLICTO_DE_VERSION")
    assert error["detalles"][0]["version_actual"] == 2

    inmutable = cliente.put(
        url, json={**_modificacion(localidad_id, 2), "codigo": "OTRO"}, headers=h_admin
    )
    _error(inmutable, 422, "CODIGO_INMUTABLE")
    mismo = cliente.put(
        url, json={**_modificacion(localidad_id, 2), "codigo": "norte"}, headers=h_admin
    )
    assert mismo.status_code == 200


def test_modificar_exige_la_version(cliente, h_admin, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    datos = _modificacion(localidad_id, 1)
    datos.pop("version")

    error = _error(
        cliente.put(f"{BASE}/{sede['id']}", json=datos, headers=h_admin), 422, "VALIDACION"
    )

    assert error["detalles"][0]["campo"] == "version"


@pytest.mark.ca("CA-SED-08", "CA-SED-21", "CA-SED-22", "CA-SED-15", "CA-SED-47", "CA-SED-36")
def test_ciclo_de_baja_y_reactivacion(cliente, h_admin, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    url = f"{BASE}/{sede['id']}"

    _error(
        cliente.post(f"{url}/baja", json={"motivo": "xx", "version": 1}, headers=h_admin),
        422,
        "VALIDACION",
    )
    baja = cliente.post(
        f"{url}/baja", json={"motivo": "Cierre por obras", "version": 1}, headers=h_admin
    )
    assert baja.status_code == 200
    assert baja.json()["estado"] == "BAJA" and baja.json()["version"] == 2
    assert baja.json()["baja"]["motivo"] == "Cierre por obras"
    assert baja.json()["baja"]["usuario"]["nombre"] == "Ana Admin"

    _error(
        cliente.post(
            f"{url}/baja", json={"motivo": "Cierre por obras", "version": 2}, headers=h_admin
        ),
        409,
        "SEDE_YA_EN_BAJA",
    )
    _error(
        cliente.put(url, json=_modificacion(localidad_id, 2), headers=h_admin), 409, "SEDE_EN_BAJA"
    )

    reactivada = cliente.post(f"{url}/reactivar", json={"version": 2}, headers=h_admin)
    assert reactivada.status_code == 200
    assert reactivada.json()["estado"] == "ACTIVA" and reactivada.json()["baja"] is None
    _error(
        cliente.post(f"{url}/reactivar", json={"version": 3}, headers=h_admin),
        409,
        "SEDE_YA_ACTIVA",
    )
    _error(
        cliente.post(f"{url}/reactivar", json={"version": 1}, headers=h_admin),
        409,
        "SEDE_YA_ACTIVA",
    )


@pytest.mark.ca("CA-SED-41")
def test_baja_con_version_vieja_se_rechaza(cliente, h_admin, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    cliente.put(
        f"{BASE}/{sede['id']}",
        json=_modificacion(localidad_id, 1, telefono="+543514999999"),
        headers=h_admin,
    )

    r = cliente.post(
        f"{BASE}/{sede['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    _error(r, 409, "CONFLICTO_DE_VERSION")


# --- excepciones de horario ------------------------------------------------------------------


def _fecha(dias: int) -> str:
    return (_hoy() + timedelta(days=dias)).isoformat()


@pytest.mark.ca("CA-SED-29", "CA-SED-33", "CA-SED-34")
def test_excepciones_se_cargan_por_rango_se_listan_y_se_quitan(
    cliente, h_admin, h_socio, localidad_id
):
    sede_id = _alta(cliente, h_admin, localidad_id).json()["id"]
    url = f"{BASE}/{sede_id}/excepciones-horario"

    creadas = cliente.post(
        url,
        json={
            "fecha_desde": _fecha(10),
            "fecha_hasta": _fecha(12),
            "tipo": "CIERRE_TOTAL",
            "motivo": "Feriados",
        },
        headers=h_admin,
    )
    assert creadas.status_code == 201
    assert [e["fecha"] for e in creadas.json()] == [_fecha(10), _fecha(11), _fecha(12)]
    parcial = cliente.post(
        url,
        json={
            "fecha_desde": _fecha(20),
            "tipo": "CIERRE_PARCIAL",
            "hora_desde": "14:00",
            "hora_hasta": "18:00",
        },
        headers=h_admin,
    )
    assert parcial.json()[0]["hora_desde"] == "14:00" and parcial.json()[0]["motivo"] is None

    para_socio = cliente.get(url, headers=h_socio).json()
    assert len(para_socio) == 4 and para_socio == sorted(para_socio, key=lambda e: e["fecha"])
    assert cliente.get(f"{BASE}/{sede_id}", headers=h_admin).json()["version"] == 1

    borrada = cliente.delete(f"{url}/{creadas.json()[1]['id']}", headers=h_admin)
    assert borrada.status_code == 204 and borrada.content == b""
    assert len(cliente.get(url, headers=h_admin).json()) == 3
    _error(cliente.delete(f"{url}/999999", headers=h_admin), 404, "EXCEPCION_HORARIO_NO_ENCONTRADA")


@pytest.mark.ca("CA-SED-31", "CA-SED-30")
def test_excepciones_invalidas_y_superpuestas(cliente, h_admin, localidad_id):
    sede_id = _alta(cliente, h_admin, localidad_id).json()["id"]
    url = f"{BASE}/{sede_id}/excepciones-horario"
    cliente.post(url, json={"fecha_desde": _fecha(5), "tipo": "CIERRE_TOTAL"}, headers=h_admin)

    pasada = cliente.post(
        url, json={"fecha_desde": _fecha(-1), "tipo": "CIERRE_TOTAL"}, headers=h_admin
    )
    _error(pasada, 422, "EXCEPCION_HORARIO_INVALIDA")
    largo = cliente.post(
        url,
        json={"fecha_desde": _fecha(10), "fecha_hasta": _fecha(50), "tipo": "CIERRE_TOTAL"},
        headers=h_admin,
    )
    _error(largo, 422, "EXCEPCION_HORARIO_INVALIDA")
    horas = cliente.post(
        url,
        json={
            "fecha_desde": _fecha(6),
            "tipo": "CIERRE_PARCIAL",
            "hora_desde": "18:00",
            "hora_hasta": "14:00",
        },
        headers=h_admin,
    )
    _error(horas, 422, "EXCEPCION_HORARIO_INVALIDA")
    solapada = cliente.post(
        url,
        json={"fecha_desde": _fecha(4), "fecha_hasta": _fecha(6), "tipo": "CIERRE_TOTAL"},
        headers=h_admin,
    )
    _error(solapada, 409, "EXCEPCION_HORARIO_SUPERPUESTA")
    assert len(cliente.get(url, headers=h_admin).json()) == 1  # todo o nada


def test_las_excepciones_pasadas_las_ve_solo_el_administrador_y_no_se_borran(
    cliente, h_admin, h_biblio, localidad_id, sesion
):
    from app.db.models import ExcepcionHorarioSedeORM

    sede = _alta(cliente, h_admin, localidad_id).json()
    pasada = ExcepcionHorarioSedeORM(
        sede_id=sede["id"],
        fecha=_hoy() - timedelta(days=3),
        tipo="CIERRE_TOTAL",
        creado_por_id=sede["creado_por"]["id"],
    )
    sesion.add(pasada)
    sesion.flush()
    url = f"{BASE}/{sede['id']}/excepciones-horario"

    assert len(cliente.get(url, params={"incluir_pasadas": True}, headers=h_admin).json()) == 1
    assert cliente.get(url, params={"incluir_pasadas": True}, headers=h_biblio).json() == []
    _error(cliente.delete(f"{url}/{pasada.id}", headers=h_admin), 422, "EXCEPCION_HORARIO_INVALIDA")


def test_no_se_cargan_excepciones_en_una_sede_en_baja(cliente, h_admin, localidad_id):
    sede = _alta(cliente, h_admin, localidad_id).json()
    cliente.post(
        f"{BASE}/{sede['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    r = cliente.post(
        f"{BASE}/{sede['id']}/excepciones-horario",
        json={"fecha_desde": _fecha(3), "tipo": "CIERRE_TOTAL"},
        headers=h_admin,
    )

    _error(r, 409, "SEDE_EN_BAJA")


# --- historial y catálogos -------------------------------------------------------------------


@pytest.mark.ca("CA-SED-34", "CA-SED-35", "CA-SED-36", "CA-SED-37")
def test_historial_del_mas_reciente_al_mas_antiguo_con_filtros(
    cliente, h_admin, h_biblio, localidad_id
):
    sede = _alta(cliente, h_admin, localidad_id).json()
    url = f"{BASE}/{sede['id']}"
    cliente.put(url, json=_modificacion(localidad_id, 1, nombre="Sede Norte 2"), headers=h_admin)
    cliente.post(f"{url}/baja", json={"motivo": "Cierre por obras", "version": 2}, headers=h_admin)

    historial = cliente.get(f"{url}/historial", headers=h_admin).json()
    assert [e["tipo_evento"] for e in historial["items"]] == ["BAJA", "MODIFICACION", "ALTA"]
    assert historial["total"] == 3
    baja = historial["items"][0]
    assert (baja["estado_anterior"], baja["estado_nuevo"], baja["motivo"]) == (
        "ACTIVA",
        "BAJA",
        "Cierre por obras",
    )
    assert baja["usuario"]["nombre"] == "Ana Admin" and baja["version_resultante"] == 3
    modificacion = historial["items"][1]
    assert {"campo": "nombre", "antes": "Sede Norte", "despues": "Sede Norte 2"} in modificacion[
        "cambios"
    ]

    filtrado = cliente.get(
        f"{url}/historial", params={"tipo_evento": "BAJA"}, headers=h_admin
    ).json()
    assert filtrado["total"] == 1
    pagina = cliente.get(f"{url}/historial", params={"page": 2, "size": 2}, headers=h_admin).json()
    assert [e["tipo_evento"] for e in pagina["items"]] == ["ALTA"]
    _error(cliente.get(f"{url}/historial", headers=h_biblio), 403, "FORBIDDEN")
    _error(cliente.get(f"{BASE}/999999/historial", headers=h_admin), 404, "SEDE_NO_ENCONTRADA")


@pytest.mark.ca("CA-SED-38")
def test_catalogos_de_provincias_y_localidades(cliente, h_socio):
    provincias = cliente.get("/api/v1/provincias", headers=h_socio).json()
    assert [p["nombre"] for p in provincias] == ["Córdoba"]

    por_texto = cliente.get(
        "/api/v1/localidades", params={"q": "RIO cuarto"}, headers=h_socio
    ).json()
    assert [(loc["nombre"], loc["provincia"]) for loc in por_texto] == [("Río Cuarto", "Córdoba")]
    todas = cliente.get(
        "/api/v1/localidades", params={"provincia_id": provincias[0]["id"]}, headers=h_socio
    ).json()
    nombres = [loc["nombre"] for loc in todas]
    assert len(todas) > 30 and nombres == sorted(nombres, key=normalizar)
