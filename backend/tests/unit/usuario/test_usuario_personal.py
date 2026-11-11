"""Reglas del dominio para el personal: alta, modificación, baja y reactivación."""

from datetime import UTC, datetime

import pytest

from app.exceptions import ErrorDeValidacion, UsuarioYaActivo, UsuarioYaEnBaja
from app.models.usuario import (
    Rol,
    SedeRef,
    Usuario,
    UsuarioRef,
    validar_clave,
    validar_nombre_usuario,
    validar_username,
)

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
ACTOR = UsuarioRef(1, "Admin")
SEDE = SedeRef(1, "CEN", "Sede Central")
OTRA = SedeRef(2, "NORTE", "Sede Norte")


def _crear(**over) -> Usuario:
    datos = {
        "username": "lucia.gomez",
        "nombre": "Lucía Gómez",
        "rol": Rol.BIBLIOTECARIO,
        "sede": SEDE,
        "password_hash": "hash",
        "actor": ACTOR,
        "ahora": AHORA,
    }
    datos.update(over)
    return Usuario.crear_personal(**datos)


def _campo(error: pytest.ExceptionInfo[ErrorDeValidacion]) -> str:
    return error.value.detalles[0]["campo"]


@pytest.mark.parametrize("texto", ["ab", "con espacio", "MAYÚS", "a" * 51, "", "x@y"])
def test_username_invalido(texto):
    with pytest.raises(ErrorDeValidacion) as error:
        validar_username(texto)
    assert _campo(error) == "username"


def test_username_se_normaliza_a_minusculas():
    assert validar_username("  Lucia.Gomez ") == "lucia.gomez"


@pytest.mark.parametrize(
    "clave", ["corta1", "sololetrasmuylarga", "1234567890123", "a" * 129 + "1"]
)
def test_clave_debil(clave):
    with pytest.raises(ErrorDeValidacion) as error:
        validar_clave(clave)
    assert _campo(error) == "password"


def test_clave_valida():
    assert validar_clave("Clave-segura-123") == "Clave-segura-123"


@pytest.mark.parametrize("nombre", ["", "  ", "ab", "a" * 101])
def test_nombre_invalido(nombre):
    with pytest.raises(ErrorDeValidacion):
        validar_nombre_usuario(nombre)


@pytest.mark.ca("CA-ACC-06")
def test_el_alta_registra_quien_y_cuando():
    usuario = _crear()

    assert usuario.activo and usuario.username == "lucia.gomez" and usuario.sede_id == 1
    assert (usuario.creado_por, usuario.creado_en) == (ACTOR, AHORA)
    assert (usuario.actualizado_por, usuario.actualizado_en) == (ACTOR, AHORA)


@pytest.mark.ca("CA-ACC-05")
def test_un_bibliotecario_sin_sede_se_rechaza():
    with pytest.raises(ErrorDeValidacion) as error:
        _crear(sede=None)
    assert _campo(error) == "sede_id"


def test_un_administrador_no_puede_tener_sede():
    with pytest.raises(ErrorDeValidacion) as error:
        _crear(rol=Rol.ADMIN, sede=SEDE)
    assert _campo(error) == "sede_id"
    assert _crear(rol=Rol.ADMIN, sede=None).sede is None


def test_el_socio_no_se_crea_como_personal():
    with pytest.raises(ErrorDeValidacion) as error:
        _crear(rol=Rol.SOCIO, sede=None)
    assert _campo(error) == "rol"


@pytest.mark.ca("CA-ACC-06", "CA-ACC-08")
def test_modificar_cambia_nombre_y_sede_y_audita():
    usuario = _crear()
    otro = UsuarioRef(9, "Otro Admin")
    despues = datetime(2026, 11, 11, tzinfo=UTC)

    cambio = usuario.modificar(nombre="Lucía G.", sede=OTRA, actor=otro, ahora=despues)

    assert cambio and (usuario.nombre, usuario.sede_id) == ("Lucía G.", 2)
    assert (usuario.actualizado_por, usuario.actualizado_en) == (otro, despues)
    assert usuario.creado_por == ACTOR and usuario.creado_en == AHORA


def test_modificar_sin_cambios_no_toca_la_auditoria():
    usuario = _crear()

    cambio = usuario.modificar(
        nombre="Lucía Gómez",
        sede=SEDE,
        actor=UsuarioRef(9, "Otro"),
        ahora=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert not cambio and usuario.actualizado_por == ACTOR and usuario.actualizado_en == AHORA


def test_modificar_no_permite_quitar_la_sede_a_un_bibliotecario_ni_darsela_a_un_admin():
    with pytest.raises(ErrorDeValidacion):
        _crear().modificar(nombre="Lucía", sede=None, actor=ACTOR, ahora=AHORA)
    with pytest.raises(ErrorDeValidacion):
        _crear(rol=Rol.ADMIN, sede=None).modificar(
            nombre="Admin", sede=SEDE, actor=ACTOR, ahora=AHORA
        )


@pytest.mark.ca("CA-ACC-14")
def test_un_usuario_no_puede_darse_de_baja_a_si_mismo():
    admin = _crear(rol=Rol.ADMIN, sede=None)
    admin.id = 1

    with pytest.raises(ErrorDeValidacion) as error:
        admin.dar_de_baja(actor=ACTOR, ahora=AHORA)

    assert admin.activo and _campo(error) == "id"


def test_baja_y_reactivacion():
    usuario = _crear()
    usuario.id = 5
    admin = UsuarioRef(1, "Admin")

    usuario.dar_de_baja(actor=admin, ahora=AHORA)
    assert not usuario.activo and usuario.sede_id == 1  # conserva su sede para poder reactivarlo
    with pytest.raises(UsuarioYaEnBaja):
        usuario.dar_de_baja(actor=admin, ahora=AHORA)

    usuario.reactivar(actor=admin, ahora=AHORA)
    assert usuario.activo
    with pytest.raises(UsuarioYaActivo):
        usuario.reactivar(actor=admin, ahora=AHORA)
