"""API de usuarios del personal y su efecto sobre las sedes."""

import pytest
from sqlalchemy import select

from app.db.models import LocalidadORM, SocioORM
from tests.controllers.test_sede_api import BASE, _alta, _error

USUARIOS = "/api/v1/usuarios"
CLAVE_NUEVA = "Clave-segura-123"


@pytest.fixture
def localidad_id(sesion) -> int:
    return sesion.scalar(select(LocalidadORM.id).where(LocalidadORM.nombre == "Córdoba"))


@pytest.fixture
def admin(crear_usuario):
    return crear_usuario("ADMIN", nombre="Ana Admin", username="ana.admin")


@pytest.fixture
def h_admin(admin, autenticar):
    return autenticar(admin)


@pytest.fixture
def sede_a(cliente, h_admin, localidad_id) -> dict:
    return _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo="SEDE_A",
        nombre="Sede A",
        calle="Calle A",
        numero="1",
    ).json()


@pytest.fixture
def sede_b(cliente, h_admin, localidad_id) -> dict:
    return _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo="SEDE_B",
        nombre="Sede B",
        calle="Calle B",
        numero="2",
    ).json()


def _alta_usuario(cliente, headers, **over):
    datos = {
        "username": "lucia.gomez",
        "password": CLAVE_NUEVA,
        "nombre": "Lucía Gómez",
        "rol": "BIBLIOTECARIO",
        "sede_id": None,
    }
    datos.update(over)
    return cliente.post(USUARIOS, json=datos, headers=headers)


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-ACC-06")
def test_el_alta_de_un_bibliotecario_responde_201_sin_exponer_la_clave(cliente, h_admin, sede_a):
    r = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"])

    assert r.status_code == 201
    usuario = r.json()
    assert r.headers["location"] == f"{USUARIOS}/{usuario['id']}"
    assert (usuario["username"], usuario["rol"], usuario["activo"]) == (
        "lucia.gomez",
        "BIBLIOTECARIO",
        True,
    )
    assert usuario["sede"] == {"id": sede_a["id"], "codigo": "SEDE_A", "nombre": "Sede A"}
    assert usuario["creado_por"]["nombre"] == "Ana Admin"
    assert "password" not in r.text and "hash" not in r.text.lower()


def test_el_nuevo_usuario_puede_iniciar_sesion(cliente, h_admin, sede_a):
    _alta_usuario(cliente, h_admin, username="Lucia.Gomez", sede_id=sede_a["id"])

    login = cliente.post(
        "/api/v1/auth/login", json={"username": "lucia.gomez", "password": CLAVE_NUEVA}
    )

    assert login.status_code == 200
    assert login.json()["usuario"]["sede"]["codigo"] == "SEDE_A"


def test_alta_de_administrador(cliente, h_admin):
    r = _alta_usuario(cliente, h_admin, username="otro.admin", rol="ADMIN")

    assert r.status_code == 201 and r.json()["sede"] is None and r.json()["sede_id"] is None


@pytest.mark.ca("CA-ACC-05")
def test_un_bibliotecario_sin_sede_responde_422(cliente, h_admin):
    error = _error(_alta_usuario(cliente, h_admin), 422, "VALIDACION")

    assert error["detalles"][0]["campo"] == "sede_id"


def test_un_administrador_con_sede_responde_422(cliente, h_admin, sede_a):
    _error(_alta_usuario(cliente, h_admin, rol="ADMIN", sede_id=sede_a["id"]), 422, "VALIDACION")


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"username": "x"}, "username"),
        ({"password": "corta"}, "password"),
        ({"nombre": ""}, "nombre"),
        ({"rol": "SOCIO"}, "rol"),
    ],
)
def test_datos_invalidos(cliente, h_admin, sede_a, cambio, campo):
    error = _error(
        _alta_usuario(cliente, h_admin, sede_id=sede_a["id"], **cambio), 422, "VALIDACION"
    )

    assert error["detalles"][0]["campo"] == campo


def test_un_rol_desconocido_o_faltante_responde_422(cliente, h_admin):
    _error(_alta_usuario(cliente, h_admin, rol="GERENTE"), 422, "VALIDACION")
    r = cliente.post(USUARIOS, json={"username": "abc"}, headers=h_admin)
    assert {"password", "nombre", "rol"} <= {
        d["campo"] for d in _error(r, 422, "VALIDACION")["detalles"]
    }


def test_un_usuario_repetido_responde_409(cliente, h_admin, sede_a):
    _alta_usuario(cliente, h_admin, sede_id=sede_a["id"])

    error = _error(
        _alta_usuario(cliente, h_admin, username="LUCIA.GOMEZ", sede_id=sede_a["id"]),
        409,
        "DUPLICADO",
    )

    assert error["detalles"][0]["campo"] == "username"


@pytest.mark.ca("CA-ACC-09", "CA-SED-25")
def test_no_se_asigna_a_una_sede_en_baja_ni_inexistente(cliente, h_admin, sede_a):
    cliente.post(
        f"{BASE}/{sede_a['id']}/baja",
        json={"motivo": "Cierre temporal", "version": 1},
        headers=h_admin,
    )

    _error(_alta_usuario(cliente, h_admin, sede_id=sede_a["id"]), 409, "SEDE_EN_BAJA")
    _error(_alta_usuario(cliente, h_admin, sede_id=999_999), 404, "SEDE_NO_ENCONTRADA")


# --- permisos --------------------------------------------------------------------------------


@pytest.mark.ca("CA-ACC-13")
@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("POST", USUARIOS),
        ("GET", USUARIOS),
        ("GET", f"{USUARIOS}/1"),
        ("PUT", f"{USUARIOS}/1"),
        ("POST", f"{USUARIOS}/1/baja"),
        ("POST", f"{USUARIOS}/1/reactivar"),
    ],
)
def test_bibliotecario_y_socio_no_administran_personal_y_sin_token_es_401(
    cliente, crear_usuario, autenticar, h_admin, sede_a, sesion, metodo, ruta
):
    biblio = crear_usuario("BIBLIOTECARIO", sede_id=sede_a["id"])
    socio_orm = SocioORM(
        numero_socio="S000001",
        tipo_documento="DNI",
        nro_documento="30000001",
        nombre="So",
        apellido="Cio",
        sede_alta_id=sede_a["id"],
    )
    sesion.add(socio_orm)
    sesion.flush()
    socio = crear_usuario("SOCIO", socio_id=socio_orm.id)

    for usuario in (biblio, socio):
        _error(
            cliente.request(metodo, ruta, json={}, headers=autenticar(usuario)), 403, "FORBIDDEN"
        )
    _error(cliente.request(metodo, ruta, json={}), 401, "TOKEN_INVALIDO")


# --- consulta --------------------------------------------------------------------------------


def test_listado_con_filtros_y_paginacion(cliente, h_admin, sede_a, sede_b):
    _alta_usuario(cliente, h_admin, username="ana.a", nombre="Ana A", sede_id=sede_a["id"])
    _alta_usuario(cliente, h_admin, username="beto.b", nombre="Beto B", sede_id=sede_b["id"])
    baja = _alta_usuario(
        cliente, h_admin, username="carla.a", nombre="Carla A", sede_id=sede_a["id"]
    ).json()
    cliente.post(f"{USUARIOS}/{baja['id']}/baja", headers=h_admin)

    def listar(**params):
        return cliente.get(USUARIOS, params=params, headers=h_admin).json()

    assert listar()["total"] == 4  # incluye a quien hace la consulta
    assert [u["username"] for u in listar(rol="BIBLIOTECARIO")["items"]] == [
        "ana.a",
        "beto.b",
        "carla.a",
    ]
    assert [u["username"] for u in listar(sede_id=sede_a["id"])["items"]] == ["ana.a", "carla.a"]
    assert [u["username"] for u in listar(activo=False)["items"]] == ["carla.a"]
    assert [u["username"] for u in listar(q="BETO")["items"]] == ["beto.b"]
    pagina = listar(rol="BIBLIOTECARIO", size=2, page=2)
    assert (pagina["page"], pagina["size"], pagina["total"], len(pagina["items"])) == (2, 2, 3, 1)
    for params in ({"page": 0}, {"size": 101}, {"rol": "X"}, {"activo": "tal vez"}):
        _error(cliente.get(USUARIOS, params=params, headers=h_admin), 422, "VALIDACION")


def test_el_listado_no_incluye_socios_y_su_detalle_es_404(
    cliente, h_admin, crear_usuario, sede_a, sesion
):
    socio_orm = SocioORM(
        numero_socio="S000002",
        tipo_documento="DNI",
        nro_documento="30000002",
        nombre="So",
        apellido="Cio",
        sede_alta_id=sede_a["id"],
    )
    sesion.add(socio_orm)
    sesion.flush()
    socio = crear_usuario("SOCIO", socio_id=socio_orm.id, username="socio.api")

    assert "socio.api" not in {
        u["username"] for u in cliente.get(USUARIOS, headers=h_admin).json()["items"]
    }
    _error(cliente.get(f"{USUARIOS}/{socio.id}", headers=h_admin), 404, "USUARIO_NO_ENCONTRADO")
    _error(
        cliente.post(f"{USUARIOS}/{socio.id}/baja", headers=h_admin), 404, "USUARIO_NO_ENCONTRADO"
    )
    _error(cliente.get(f"{USUARIOS}/999999", headers=h_admin), 404, "USUARIO_NO_ENCONTRADO")


# --- modificación y reasignación -------------------------------------------------------------


@pytest.mark.ca("CA-ACC-08", "CA-ACC-06")
def test_la_reasignacion_rige_desde_la_siguiente_solicitud_con_el_mismo_token(
    cliente, h_admin, autenticar, sede_a, sede_b, sesion
):
    creado = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    from app.db.models import UsuarioORM

    token = autenticar(sesion.get(UsuarioORM, creado["id"]))
    assert cliente.get("/api/v1/auth/me", headers=token).json()["sede"]["codigo"] == "SEDE_A"

    r = cliente.put(
        f"{USUARIOS}/{creado['id']}",
        json={"nombre": "Lucía G.", "sede_id": sede_b["id"]},
        headers=h_admin,
    )

    assert r.status_code == 200
    assert (r.json()["nombre"], r.json()["sede"]["codigo"]) == ("Lucía G.", "SEDE_B")
    assert (
        r.json()["creado_por"]["nombre"] == "Ana Admin"
        and r.json()["actualizado_por"]["nombre"] == "Ana Admin"
    )
    assert cliente.get("/api/v1/auth/me", headers=token).json()["sede"]["codigo"] == "SEDE_B"
    assert (
        cliente.get(f"{USUARIOS}/{creado['id']}", headers=h_admin).json()["sede_id"] == sede_b["id"]
    )


@pytest.mark.ca("CA-ACC-09")
def test_no_se_reasigna_a_una_sede_en_baja(cliente, h_admin, sede_a, sede_b):
    creado = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    cliente.post(
        f"{BASE}/{sede_b['id']}/baja",
        json={"motivo": "Cierre temporal", "version": 1},
        headers=h_admin,
    )

    r = cliente.put(
        f"{USUARIOS}/{creado['id']}",
        json={"nombre": "Lucía", "sede_id": sede_b["id"]},
        headers=h_admin,
    )

    _error(r, 409, "SEDE_EN_BAJA")
    assert (
        cliente.get(f"{USUARIOS}/{creado['id']}", headers=h_admin).json()["sede_id"] == sede_a["id"]
    )


def test_modificar_valida_el_nombre_y_la_combinacion_rol_sede(cliente, h_admin, sede_a):
    biblio = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    admin2 = _alta_usuario(cliente, h_admin, username="otro.admin", rol="ADMIN").json()

    _error(
        cliente.put(
            f"{USUARIOS}/{biblio['id']}",
            json={"nombre": "x", "sede_id": sede_a["id"]},
            headers=h_admin,
        ),
        422,
        "VALIDACION",
    )
    _error(
        cliente.put(f"{USUARIOS}/{biblio['id']}", json={"nombre": "Lucía"}, headers=h_admin),
        422,
        "VALIDACION",
    )
    _error(
        cliente.put(
            f"{USUARIOS}/{admin2['id']}",
            json={"nombre": "Otro", "sede_id": sede_a["id"]},
            headers=h_admin,
        ),
        422,
        "VALIDACION",
    )
    _error(
        cliente.put(f"{USUARIOS}/999999", json={"nombre": "Lucía"}, headers=h_admin),
        404,
        "USUARIO_NO_ENCONTRADO",
    )
    assert (
        cliente.put(
            f"{USUARIOS}/{admin2['id']}", json={"nombre": "Otro Admin"}, headers=h_admin
        ).status_code
        == 200
    )


# --- baja y reactivación ---------------------------------------------------------------------


@pytest.mark.ca("CA-ACC-12")
def test_un_usuario_dado_de_baja_pierde_el_acceso_aunque_tenga_token_vigente(
    cliente, h_admin, autenticar, sede_a, sesion
):
    from app.db.models import UsuarioORM

    creado = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    token = autenticar(sesion.get(UsuarioORM, creado["id"]))
    assert cliente.get("/api/v1/auth/me", headers=token).status_code == 200

    cliente.post(f"{USUARIOS}/{creado['id']}/baja", headers=h_admin)

    _error(cliente.get("/api/v1/auth/me", headers=token), 401, "TOKEN_INVALIDO")
    login = cliente.post(
        "/api/v1/auth/login", json={"username": "lucia.gomez", "password": CLAVE_NUEVA}
    )
    _error(login, 401, "CREDENCIALES_INVALIDAS")


@pytest.mark.ca("CA-ACC-14")
def test_el_administrador_no_puede_darse_de_baja_a_si_mismo(cliente, h_admin, admin):
    error = _error(cliente.post(f"{USUARIOS}/{admin.id}/baja", headers=h_admin), 422, "VALIDACION")

    assert error["detalles"][0]["campo"] == "id"
    assert cliente.get("/api/v1/auth/me", headers=h_admin).status_code == 200


def test_ciclo_de_baja_y_reactivacion(cliente, h_admin, sede_a):
    creado = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    url = f"{USUARIOS}/{creado['id']}"

    _error(cliente.post(f"{url}/reactivar", headers=h_admin), 409, "USUARIO_YA_ACTIVO")
    baja = cliente.post(f"{url}/baja", headers=h_admin)
    assert baja.status_code == 200 and baja.json()["activo"] is False
    assert baja.json()["sede_id"] == sede_a["id"]
    _error(cliente.post(f"{url}/baja", headers=h_admin), 409, "USUARIO_YA_EN_BAJA")
    reactivado = cliente.post(f"{url}/reactivar", headers=h_admin)
    assert reactivado.status_code == 200 and reactivado.json()["activo"] is True
    login = cliente.post(
        "/api/v1/auth/login", json={"username": "lucia.gomez", "password": CLAVE_NUEVA}
    )
    assert login.status_code == 200


@pytest.mark.ca("CA-ACC-09")
def test_reactivar_con_la_sede_en_baja_exige_reasignar_primero(cliente, h_admin, sede_a, sede_b):
    creado = _alta_usuario(cliente, h_admin, sede_id=sede_a["id"]).json()
    url = f"{USUARIOS}/{creado['id']}"
    cliente.post(f"{url}/baja", headers=h_admin)
    cliente.post(
        f"{BASE}/{sede_a['id']}/baja",
        json={"motivo": "Cierre temporal", "version": 1},
        headers=h_admin,
    )

    _error(cliente.post(f"{url}/reactivar", headers=h_admin), 409, "SEDE_EN_BAJA")
    cliente.put(url, json={"nombre": creado["nombre"], "sede_id": sede_b["id"]}, headers=h_admin)
    assert cliente.post(f"{url}/reactivar", headers=h_admin).json()["sede"]["codigo"] == "SEDE_B"


# --- efecto sobre la baja de sede ------------------------------------------------------------


@pytest.mark.ca("CA-SED-16", "CA-SED-07", "CA-SED-22", "CA-ACC-10")
def test_los_bibliotecarios_activos_bloquean_la_baja_de_su_sede_hasta_reasignarlos(
    cliente, h_admin, sede_a, sede_b
):
    uno = _alta_usuario(
        cliente, h_admin, username="uno.a", nombre="Uno A", sede_id=sede_a["id"]
    ).json()
    dos = _alta_usuario(
        cliente, h_admin, username="dos.a", nombre="Dos A", sede_id=sede_a["id"]
    ).json()
    baja = f"{BASE}/{sede_a['id']}/baja"
    pedido = {"motivo": "Cierre por obras", "version": 1}

    bloqueada = cliente.post(baja, json=pedido, headers=h_admin)
    error = _error(bloqueada, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")
    assert "2 bibliotecarios asignados" in error["mensaje"]
    [impedimento] = error["detalles"]
    assert (impedimento["tipo"], impedimento["cantidad"], impedimento["hay_mas"]) == (
        "BIBLIOTECARIOS_ASIGNADOS",
        2,
        False,
    )
    assert {e["referencia"] for e in impedimento["elementos"]} == {"uno.a", "dos.a"}
    assert cliente.get(f"{BASE}/{sede_a['id']}", headers=h_admin).json()["estado"] == "ACTIVA"

    cliente.post(f"{USUARIOS}/{uno['id']}/baja", headers=h_admin)  # uno deja de contar
    cliente.put(
        f"{USUARIOS}/{dos['id']}",
        json={"nombre": "Dos A", "sede_id": sede_b["id"]},
        headers=h_admin,
    )

    assert cliente.post(baja, json=pedido, headers=h_admin).status_code == 200


def test_un_bibliotecario_de_otra_sede_no_bloquea(cliente, h_admin, sede_a, sede_b):
    _alta_usuario(cliente, h_admin, sede_id=sede_b["id"])

    r = cliente.post(
        f"{BASE}/{sede_a['id']}/baja",
        json={"motivo": "Cierre por obras", "version": 1},
        headers=h_admin,
    )

    assert r.status_code == 200
