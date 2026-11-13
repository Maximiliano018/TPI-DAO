"""API de socios contra PostgreSQL (alta, búsqueda, estados, cuenta y permisos por rol)."""

import pytest
from sqlalchemy import select, text

from app.db.models import LocalidadORM, SocioORM
from tests.controllers.test_sede_api import _alta, _error

SOCIOS = "/api/v1/socios"


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
def sede(cliente, h_admin, localidad_id) -> dict:
    return _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo="SEDE_S",
        nombre="Sede S",
        calle="Calle S",
        numero="9",
    ).json()


@pytest.fixture
def h_biblio(crear_usuario, autenticar, sede):
    return autenticar(crear_usuario("BIBLIOTECARIO", sede_id=sede["id"], nombre="Beto Biblio"))


def _cuerpo(**over) -> dict:
    datos = {
        "tipo_documento": "DNI",
        "nro_documento": "30.111.222",
        "nombre": "Lucía",
        "apellido": "Gómez",
        "fecha_nacimiento": "1995-04-12",
        "email": "Lucia@Example.com",
        "telefono": "+54 351 500-0000",
        "domicilio": "San Martín 123",
    }
    datos.update(over)
    return datos


def _alta_socio(cliente, headers, **over):
    return cliente.post(SOCIOS, json=_cuerpo(**over), headers=headers)


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-01")
def test_el_alta_responde_201_con_numero_de_socio_y_estado_habilitado(
    cliente, h_biblio, sede, sesion
):
    r = _alta_socio(cliente, h_biblio)

    assert r.status_code == 201, r.json()
    socio = r.json()
    assert r.headers["location"] == f"{SOCIOS}/{socio['id']}"
    assert socio["numero_socio"].isdigit() and len(socio["numero_socio"]) >= 5
    assert (socio["estado"], socio["sede_alta_id"], socio["sede_alta"]) == (
        "HABILITADO",
        sede["id"],
        "Sede S",
    )
    assert (socio["nro_documento"], socio["email"], socio["telefono"]) == (
        "30111222",
        "lucia@example.com",
        "+543515000000",
    )
    assert socio["creado_por"]["nombre"] == "Beto Biblio" and socio["cuenta"] is None
    otro = _alta_socio(cliente, h_biblio, nro_documento="40111222", nombre="Juan").json()
    assert int(otro["numero_socio"]) == int(socio["numero_socio"]) + 1


@pytest.mark.ca("CA-SOC-02")
def test_el_documento_repetido_responde_409_con_el_socio_existente(cliente, h_biblio):
    existente = _alta_socio(cliente, h_biblio).json()

    r = _alta_socio(cliente, h_biblio, nro_documento="30111222", nombre="Otra", apellido="P")

    error = _error(r, 409, "DUPLICADO")
    assert error["detalles"][0]["socio_id"] == existente["id"]
    assert error["detalles"][0]["puede_reactivarse"] is False


@pytest.mark.ca("CA-SOC-03")
def test_un_socio_dado_de_baja_se_reactiva_en_lugar_de_duplicarse(cliente, h_biblio, h_admin):
    existente = _alta_socio(cliente, h_biblio).json()
    baja = cliente.post(
        f"{SOCIOS}/{existente['id']}/baja", json={"motivo": "Se mudó de ciudad"}, headers=h_admin
    )
    assert baja.json()["estado"] == "BAJA"

    error = _error(_alta_socio(cliente, h_biblio), 409, "DUPLICADO")
    assert error["detalles"][0]["puede_reactivarse"] is True

    r = cliente.post(f"{SOCIOS}/{existente['id']}/reactivar", headers=h_admin)
    assert (r.status_code, r.json()["estado"], r.json()["fecha_baja"]) == (200, "HABILITADO", None)


def test_un_posible_duplicado_se_rechaza_hasta_confirmarlo(cliente, h_biblio):
    existente = _alta_socio(cliente, h_biblio).json()

    error = _error(
        _alta_socio(cliente, h_biblio, nro_documento="40111222", nombre="LUCIA", apellido="gomez"),
        409,
        "POSIBLE_DUPLICADO",
    )
    assert error["detalles"][0]["socio_id"] == existente["id"]

    r = _alta_socio(cliente, h_biblio, nro_documento="40111222", confirmar_posible_duplicado=True)
    assert r.status_code == 201


@pytest.mark.parametrize(
    ("over", "campo"),
    [
        ({"nro_documento": "12"}, "nro_documento"),
        ({"nombre": " "}, "nombre"),
        ({"email": None, "telefono": None}, "email"),
        ({"telefono": "351 5000000"}, "telefono"),
        ({"fecha_nacimiento": "2999-01-01"}, "fecha_nacimiento"),
        ({"tipo_documento": "CUIT"}, "tipo_documento"),
    ],
)
def test_datos_invalidos_responden_422(cliente, h_biblio, over, campo):
    error = _error(_alta_socio(cliente, h_biblio, **over), 422, "VALIDACION")
    assert error["detalles"][0]["campo"] == campo


@pytest.mark.ca("CA-SED-24")
def test_el_alta_en_una_sede_en_baja_se_rechaza(cliente, h_admin, sede):
    cliente.post(
        f"/api/v1/sedes/{sede['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": sede["version"]},
        headers=h_admin,
    )

    _error(_alta_socio(cliente, h_admin, sede_alta_id=sede["id"]), 409, "SEDE_EN_BAJA")


def test_el_administrador_debe_indicar_la_sede_y_esta_debe_existir(cliente, h_admin):
    _error(_alta_socio(cliente, h_admin), 422, "VALIDACION")
    _error(_alta_socio(cliente, h_admin, sede_alta_id=999999), 404, "SEDE_NO_ENCONTRADA")


def test_la_busqueda_previa_devuelve_coincidencias(cliente, h_biblio):
    existente = _alta_socio(cliente, h_biblio).json()

    r = cliente.get(
        f"{SOCIOS}/posibles-duplicados",
        params={"nombre": "lucía", "apellido": "GÓMEZ", "fecha_nacimiento": "1995-04-12"},
        headers=h_biblio,
    )
    por_documento = cliente.get(
        f"{SOCIOS}/posibles-duplicados",
        params={"tipo_documento": "DNI", "nro_documento": "30111222"},
        headers=h_biblio,
    )

    assert [s["id"] for s in r.json()] == [existente["id"]]
    assert [s["id"] for s in por_documento.json()] == [existente["id"]]


# --- búsqueda y ficha ------------------------------------------------------------------------


def test_la_busqueda_filtra_por_apellido_documento_numero_y_estado(cliente, h_biblio, h_admin):
    lucia = _alta_socio(cliente, h_biblio).json()
    juan = _alta_socio(
        cliente, h_biblio, nro_documento="40111222", nombre="Juan", apellido="Álvarez"
    ).json()
    cliente.post(f"{SOCIOS}/{juan['id']}/baja", json={"motivo": "Se mudó"}, headers=h_admin)

    def apellidos(**params):
        return [
            s["apellido"]
            for s in cliente.get(SOCIOS, params=params, headers=h_biblio).json()["items"]
        ]

    assert apellidos() == ["Álvarez", "Gómez"]
    assert apellidos(q="alvarez") == ["Álvarez"]
    assert apellidos(q="juan alv") == ["Álvarez"]
    assert apellidos(q="30.111.222") == ["Gómez"]
    assert apellidos(q=lucia["numero_socio"]) == ["Gómez"]
    assert apellidos(documento="40111222") == ["Álvarez"]
    assert apellidos(estado="BAJA") == ["Álvarez"]
    pagina = cliente.get(SOCIOS, params={"size": 1, "page": 2}, headers=h_biblio).json()
    assert (pagina["total"], len(pagina["items"]), pagina["page"]) == (2, 1, 2)


def test_la_ficha_trae_datos_y_situacion(cliente, h_biblio):
    socio = _alta_socio(cliente, h_biblio).json()

    ficha = cliente.get(f"{SOCIOS}/{socio['id']}", headers=h_biblio).json()

    assert ficha["domicilio"] == "San Martín 123"
    assert ficha["situacion"] == {
        "prestamos_activos": 0,
        "prestamos_vencidos": 0,
        "multas_pendientes": 0,
        "reservas_activas": 0,
    }
    _error(cliente.get(f"{SOCIOS}/999999", headers=h_biblio), 404, "SOCIO_NO_ENCONTRADO")


def test_modificar_reemplaza_los_datos_y_rechaza_un_documento_ajeno(cliente, h_biblio):
    lucia = _alta_socio(cliente, h_biblio).json()
    juan = _alta_socio(cliente, h_biblio, nro_documento="40111222", nombre="Juan").json()

    r = cliente.put(f"{SOCIOS}/{lucia['id']}", json=_cuerpo(apellido="Pérez"), headers=h_biblio)
    assert (r.status_code, r.json()["apellido"]) == (200, "Pérez")
    _error(
        cliente.put(f"{SOCIOS}/{juan['id']}", json=_cuerpo(nombre="Juan"), headers=h_biblio),
        409,
        "DUPLICADO",
    )


# --- estados ---------------------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-10")
def test_inhabilitacion_administrativa_y_quien_la_levanta(cliente, h_biblio, h_admin):
    socio = _alta_socio(cliente, h_biblio).json()
    ruta = f"{SOCIOS}/{socio['id']}"

    _error(
        cliente.post(f"{ruta}/inhabilitar", json={"motivo": "Daño reiterado"}, headers=h_biblio),
        403,
        "FORBIDDEN",
    )
    r = cliente.post(f"{ruta}/inhabilitar", json={"motivo": "Daño reiterado"}, headers=h_admin)
    assert (r.json()["estado"], r.json()["motivo_inhabilitacion"]) == (
        "INHABILITADO",
        "ADMINISTRATIVA",
    )
    _error(
        cliente.post(f"{ruta}/inhabilitar", json={"motivo": "Otra vez"}, headers=h_admin),
        409,
        "SOCIO_YA_INHABILITADO",
    )
    _error(cliente.post(f"{ruta}/rehabilitar", headers=h_biblio), 403, "FORBIDDEN")
    r = cliente.post(f"{ruta}/rehabilitar", headers=h_admin)
    assert (r.json()["estado"], r.json()["motivo_administrativo"]) == ("HABILITADO", None)
    _error(cliente.post(f"{ruta}/rehabilitar", headers=h_biblio), 409, "SOCIO_YA_HABILITADO")


def test_baja_y_reactivacion_validan_el_estado(cliente, h_biblio, h_admin):
    socio = _alta_socio(cliente, h_biblio).json()
    ruta = f"{SOCIOS}/{socio['id']}"

    _error(cliente.post(f"{ruta}/reactivar", headers=h_admin), 409, "SOCIO_YA_ACTIVO")
    _error(cliente.post(f"{ruta}/baja", json={"motivo": "x"}, headers=h_admin), 422, "VALIDACION")
    cliente.post(f"{ruta}/baja", json={"motivo": "Se mudó de ciudad"}, headers=h_admin)
    _error(
        cliente.post(f"{ruta}/baja", json={"motivo": "Se mudó de ciudad"}, headers=h_admin),
        409,
        "SOCIO_YA_EN_BAJA",
    )
    _error(cliente.put(ruta, json=_cuerpo(), headers=h_biblio), 409, "SOCIO_EN_BAJA")


# --- cuenta del socio y permisos -------------------------------------------------------------


@pytest.mark.ca("CA-SOC-11")
def test_el_socio_entra_con_su_cuenta_y_ve_solo_su_ficha(cliente, h_biblio):
    socio = _alta_socio(cliente, h_biblio).json()
    otro = _alta_socio(cliente, h_biblio, nro_documento="40111222", nombre="Juan").json()

    r = cliente.post(
        f"{SOCIOS}/{socio['id']}/cuenta",
        json={"username": "Lucia.Gomez", "password": "Clave-segura-123"},
        headers=h_biblio,
    )
    assert (r.status_code, r.json()["cuenta"]["username"]) == (201, "lucia.gomez")
    _error(
        cliente.post(
            f"{SOCIOS}/{socio['id']}/cuenta",
            json={"username": "otra.cuenta", "password": "Clave-segura-123"},
            headers=h_biblio,
        ),
        409,
        "SOCIO_CON_CUENTA",
    )

    login = cliente.post(
        "/api/v1/auth/login", json={"username": "lucia.gomez", "password": "Clave-segura-123"}
    ).json()
    h_socio = {"Authorization": f"Bearer {login['access_token']}"}
    yo = cliente.get("/api/v1/auth/me", headers=h_socio).json()
    assert (yo["rol"], yo["socio_id"]) == ("SOCIO", socio["id"])
    assert cliente.get(f"{SOCIOS}/{socio['id']}", headers=h_socio).status_code == 200
    _error(cliente.get(f"{SOCIOS}/{otro['id']}", headers=h_socio), 404, "SOCIO_NO_ENCONTRADO")
    _error(cliente.get(SOCIOS, headers=h_socio), 403, "FORBIDDEN")


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("POST", SOCIOS),
        ("PUT", f"{SOCIOS}/1"),
        ("POST", f"{SOCIOS}/1/rehabilitar"),
        ("POST", f"{SOCIOS}/1/cuenta"),
    ],
)
def test_un_socio_no_registra_ni_modifica_socios_y_sin_token_es_401(
    cliente, crear_usuario, autenticar, sede, sesion, metodo, ruta
):
    socio_orm = SocioORM(
        numero_socio="S000003",
        tipo_documento="DNI",
        nro_documento="30000003",
        nombre="So",
        apellido="Cio",
        email="so@example.com",
        sede_alta_id=sede["id"],
    )
    sesion.add(socio_orm)
    sesion.flush()
    usuario = crear_usuario("SOCIO", socio_id=socio_orm.id)

    _error(cliente.request(metodo, ruta, json={}, headers=autenticar(usuario)), 403, "FORBIDDEN")
    _error(cliente.request(metodo, ruta, json={}), 401, "TOKEN_INVALIDO")


@pytest.mark.parametrize("accion", ["inhabilitar", "baja", "reactivar"])
def test_el_bibliotecario_no_inhabilita_ni_da_de_baja(cliente, h_biblio, accion):
    socio = _alta_socio(cliente, h_biblio).json()

    r = cliente.post(
        f"{SOCIOS}/{socio['id']}/{accion}", json={"motivo": "Motivo válido"}, headers=h_biblio
    )

    _error(r, 403, "FORBIDDEN")


# --- base de datos ---------------------------------------------------------------------------


def test_la_base_rechaza_estados_inconsistentes(sesion, sede):
    socio = SocioORM(
        numero_socio="S000004",
        tipo_documento="DNI",
        nro_documento="30000004",
        nombre="So",
        apellido="Cio",
        sede_alta_id=sede["id"],
        estado="INHABILITADO",
    )
    sesion.add(socio)
    with pytest.raises(Exception, match="ck_socio_inhabilitado_con_motivo"):
        sesion.flush()
    sesion.rollback()


def test_la_secuencia_de_numeros_no_repite(sesion):
    primero = sesion.scalar(text("SELECT nextval('socio_numero_seq')"))
    segundo = sesion.scalar(text("SELECT nextval('socio_numero_seq')"))
    assert segundo == primero + 1
