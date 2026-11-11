"""Inicio de sesión y verificación de tokens (repositorio en memoria)."""

from datetime import timedelta

import pytest

from app.config import Settings
from app.config.security import crear_token
from app.exceptions import CredencialesInvalidas, TokenInvalido
from app.models.usuario import SedeRef
from app.services.auth_service import AuthService
from tests.factories.dominio import CLAVE_DE_PRUEBA, BibliotecarioFactory
from tests.fakes.reloj import RelojFijo
from tests.fakes.repositorios import UnitOfWorkEnMemoria

SETTINGS = Settings(secret_key="clave-de-pruebas-con-mas-de-treinta-y-dos-caracteres")


@pytest.fixture
def uow() -> UnitOfWorkEnMemoria:
    uow = UnitOfWorkEnMemoria()
    uow.usuarios.agregar(BibliotecarioFactory(id=7, username="mlopez"))
    return uow


def _servicio(uow: UnitOfWorkEnMemoria, reloj: RelojFijo) -> AuthService:
    return AuthService(uow, reloj, SETTINGS)


def test_login_correcto_emite_un_token_que_identifica_al_usuario(uow, reloj):
    servicio = _servicio(uow, reloj)

    resultado = servicio.login("MLopez ", CLAVE_DE_PRUEBA)

    assert resultado.usuario.username == "mlopez"
    assert resultado.expira_en_segundos == 3600
    assert servicio.autenticar(resultado.token).id == 7


@pytest.mark.ca("CA-ACC-07")
@pytest.mark.parametrize(
    ("username", "password"),
    [("mlopez", "otra-clave"), ("inexistente", CLAVE_DE_PRUEBA), ("", "")],
)
def test_credenciales_invalidas_no_revelan_cual_dato_fallo(uow, reloj, username, password):
    with pytest.raises(CredencialesInvalidas) as error:
        _servicio(uow, reloj).login(username, password)

    assert error.value.mensaje == "Usuario o contraseña incorrectos."


def test_un_usuario_dado_de_baja_no_puede_iniciar_sesion(uow, reloj):
    uow.usuarios.obtener(7).activo = False

    with pytest.raises(CredencialesInvalidas):
        _servicio(uow, reloj).login("mlopez", CLAVE_DE_PRUEBA)


@pytest.mark.ca("CA-ACC-11")
def test_un_token_vencido_es_rechazado(uow, reloj):
    servicio = _servicio(uow, reloj)
    token = servicio.login("mlopez", CLAVE_DE_PRUEBA).token

    reloj.avanzar(horas=2)
    token_nuevo_instante = crear_token(
        usuario_id=7,
        rol="BIBLIOTECARIO",
        sede_id=1,
        ahora=reloj.ahora() - timedelta(hours=3),
        minutos=60,
        clave=SETTINGS.secret_key,
    )

    with pytest.raises(TokenInvalido):
        servicio.autenticar(token_nuevo_instante)
    assert token  # el token original era válido al emitirse


@pytest.mark.ca("CA-ACC-11")
def test_un_token_manipulado_o_con_otra_clave_es_rechazado(uow, reloj):
    servicio = _servicio(uow, reloj)
    ajeno = crear_token(
        usuario_id=7,
        rol="ADMIN",
        sede_id=None,
        ahora=reloj.ahora(),
        minutos=60,
        clave="otra-clave-distinta-de-mas-de-treinta-y-dos-caracteres",
    )

    for malo in (ajeno, "no.es.un.token", ""):
        with pytest.raises(TokenInvalido):
            servicio.autenticar(malo)


@pytest.mark.ca("CA-ACC-12")
def test_un_usuario_dado_de_baja_con_token_vigente_es_rechazado(uow, reloj):
    servicio = _servicio(uow, reloj)
    token = servicio.login("mlopez", CLAVE_DE_PRUEBA).token
    uow.usuarios.obtener(7).activo = False

    with pytest.raises(TokenInvalido):
        servicio.autenticar(token)


@pytest.mark.ca("CA-ACC-08")
def test_el_usuario_se_recarga_en_cada_solicitud_y_refleja_la_reasignacion(uow, reloj):
    servicio = _servicio(uow, reloj)
    token = servicio.login("mlopez", CLAVE_DE_PRUEBA).token
    assert servicio.autenticar(token).sede_id == 1

    uow.usuarios.obtener(7).sede = SedeRef(2, "NORTE", "Sede Norte")

    assert servicio.autenticar(token).sede_id == 2


def test_un_token_de_un_usuario_inexistente_es_rechazado(uow, reloj):
    servicio = _servicio(uow, reloj)
    token = crear_token(
        usuario_id=999,
        rol="ADMIN",
        sede_id=None,
        ahora=reloj.ahora(),
        minutos=60,
        clave=SETTINGS.secret_key,
    )

    with pytest.raises(TokenInvalido):
        servicio.autenticar(token)
