"""Roles y permisos: el mapa rol → permisos es la única fuente de verdad."""

import pytest

from app.exceptions import PermisoDenegado
from app.models.usuario import ROL_PERMISOS, Permiso, Rol
from tests.factories.dominio import BibliotecarioFactory, SocioUsuarioFactory, UsuarioFactory


def test_todo_rol_tiene_permisos_definidos():
    assert set(ROL_PERMISOS) == set(Rol)


@pytest.mark.parametrize(
    ("factory", "permiso", "esperado"),
    [
        (UsuarioFactory, Permiso.SEDE_ADMINISTRAR, True),
        (UsuarioFactory, Permiso.USUARIO_ADMINISTRAR, True),
        (UsuarioFactory, Permiso.SEDE_VER_HISTORIAL, True),
        (BibliotecarioFactory, Permiso.SEDE_LEER_BASICO, True),
        (BibliotecarioFactory, Permiso.SEDE_LEER_COMPLETO, False),
        (BibliotecarioFactory, Permiso.SEDE_ADMINISTRAR, False),
        (BibliotecarioFactory, Permiso.USUARIO_ADMINISTRAR, False),
        (SocioUsuarioFactory, Permiso.SEDE_LEER_PUBLICO, True),
        (SocioUsuarioFactory, Permiso.SEDE_LEER_BASICO, False),
        (SocioUsuarioFactory, Permiso.SEDE_ADMINISTRAR, False),
    ],
)
def test_los_permisos_dependen_solo_del_rol(factory, permiso, esperado):
    assert factory().puede(permiso) is esperado


@pytest.mark.ca("CA-ACC-03", "CA-ACC-13")
def test_exigir_un_permiso_que_no_se_tiene_lanza_permiso_denegado():
    with pytest.raises(PermisoDenegado) as error:
        BibliotecarioFactory().exigir(Permiso.USUARIO_ADMINISTRAR)

    assert error.value.codigo == "FORBIDDEN"


def test_un_bibliotecario_opera_solo_en_su_sede_y_el_administrador_en_ninguna_por_sede():
    bibliotecario = BibliotecarioFactory()

    assert bibliotecario.opera_en(1) is True
    assert bibliotecario.opera_en(2) is False
    assert UsuarioFactory().opera_en(1) is False
    assert SocioUsuarioFactory().opera_en(1) is False


def test_el_administrador_y_el_socio_no_tienen_sede_asignada():
    assert UsuarioFactory().sede_id is None
    assert SocioUsuarioFactory().sede_id is None
