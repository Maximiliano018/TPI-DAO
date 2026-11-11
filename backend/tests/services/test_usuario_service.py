"""Casos de uso del personal con repositorios en memoria."""

import pytest

from app.exceptions import (
    DuplicadoError,
    ErrorDeValidacion,
    PermisoDenegado,
    SedeEnBaja,
    SedeNoEncontrada,
    UsuarioNoEncontrado,
    UsuarioYaActivo,
    UsuarioYaEnBaja,
)
from app.models.usuario import Rol
from app.services.sede_service import SedeService
from app.services.usuario_service import DatosUsuarioNuevo, UsuarioService
from tests.factories.dominio import BibliotecarioFactory, SocioUsuarioFactory, UsuarioFactory
from tests.factories.sede import datos_sede
from tests.fakes.repositorios import UnitOfWorkEnMemoria
from tests.fakes.verificadores import verificador_con

ADMIN = UsuarioFactory(id=100, nombre="Admin")


@pytest.fixture
def uow() -> UnitOfWorkEnMemoria:
    return UnitOfWorkEnMemoria()


@pytest.fixture
def sedes(uow, reloj):
    servicio = SedeService(uow, reloj, verificador_con())
    return {
        "centro": servicio.crear(ADMIN, "CEN", datos_sede(nombre="Centro")).sede,
        "norte": servicio.crear(ADMIN, "NORTE", datos_sede(nombre="Norte")).sede,
    }


@pytest.fixture
def servicio(uow, reloj) -> UsuarioService:
    return UsuarioService(uow, reloj, hashear=lambda clave: f"hash:{clave}")


def _nuevo(**over) -> DatosUsuarioNuevo:
    datos = {
        "username": "lucia.gomez",
        "password": "Clave-segura-123",
        "nombre": "Lucía Gómez",
        "rol": Rol.BIBLIOTECARIO,
        "sede_id": None,
    }
    datos.update(over)
    return DatosUsuarioNuevo(**datos)


def _biblio(servicio, sedes, sede="centro", **over):
    return servicio.crear(ADMIN, _nuevo(sede_id=sedes[sede].id, **over))


@pytest.mark.ca("CA-ACC-13")
@pytest.mark.parametrize("actor", [BibliotecarioFactory(id=2), SocioUsuarioFactory(id=3)])
def test_solo_el_administrador_gestiona_personal(servicio, sedes, actor):
    usuario = _biblio(servicio, sedes)

    for accion in (
        lambda: servicio.crear(actor, _nuevo(username="otro.user", sede_id=sedes["centro"].id)),
        lambda: servicio.modificar(actor, usuario.id, "Nuevo nombre", sedes["centro"].id),
        lambda: servicio.dar_de_baja(actor, usuario.id),
        lambda: servicio.reactivar(actor, usuario.id),
        lambda: servicio.obtener(actor, usuario.id),
        lambda: servicio.listar(actor, None, None, None, None, 1, 20),
    ):
        with pytest.raises(PermisoDenegado):
            accion()


@pytest.mark.ca("CA-ACC-06")
def test_el_alta_guarda_el_hash_la_sede_y_la_auditoria(servicio, sedes, uow):
    usuario = _biblio(servicio, sedes, username="  Lucia.Gomez ")

    assert usuario.id and usuario.username == "lucia.gomez" and usuario.activo
    assert usuario.password_hash == "hash:Clave-segura-123" and "Clave-segura" not in usuario.nombre
    assert usuario.sede.codigo == "CEN" and usuario.creado_por.id == 100
    assert uow.confirmaciones >= 1


def test_el_alta_de_un_administrador_no_lleva_sede(servicio, sedes):
    admin = servicio.crear(ADMIN, _nuevo(username="otro.admin", rol=Rol.ADMIN))

    assert admin.rol == Rol.ADMIN and admin.sede is None
    with pytest.raises(ErrorDeValidacion):
        servicio.crear(
            ADMIN, _nuevo(username="admin.dos", rol=Rol.ADMIN, sede_id=sedes["centro"].id)
        )


@pytest.mark.ca("CA-ACC-05")
def test_un_bibliotecario_sin_sede_se_rechaza_y_no_se_guarda(servicio, uow):
    with pytest.raises(ErrorDeValidacion) as error:
        servicio.crear(ADMIN, _nuevo())

    assert error.value.detalles[0]["campo"] == "sede_id"
    assert uow.usuarios.obtener_por_username("lucia.gomez") is None


@pytest.mark.parametrize(
    ("cambio", "campo"),
    [
        ({"username": "x"}, "username"),
        ({"password": "corta"}, "password"),
        ({"nombre": " "}, "nombre"),
        ({"rol": Rol.SOCIO}, "rol"),
    ],
)
def test_datos_invalidos(servicio, sedes, cambio, campo):
    with pytest.raises(ErrorDeValidacion) as error:
        _biblio(servicio, sedes, **cambio)

    assert error.value.detalles[0]["campo"] == campo


def test_un_usuario_repetido_se_rechaza_sin_distinguir_mayusculas(servicio, sedes):
    _biblio(servicio, sedes)

    with pytest.raises(DuplicadoError) as error:
        _biblio(servicio, sedes, username="LUCIA.GOMEZ")

    assert error.value.codigo == "DUPLICADO"


@pytest.mark.ca("CA-ACC-09", "CA-SED-25")
def test_no_se_asigna_un_bibliotecario_a_una_sede_en_baja_ni_inexistente(
    servicio, sedes, uow, reloj
):
    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, sedes["norte"].id, 1, "Cierre temporal"
    )

    with pytest.raises(SedeEnBaja) as error:
        _biblio(servicio, sedes, sede="norte")
    assert error.value.detalles[0]["campo"] == "sede_id"
    with pytest.raises(SedeNoEncontrada):
        servicio.crear(ADMIN, _nuevo(sede_id=999))


@pytest.mark.ca("CA-ACC-08", "CA-ACC-09")
def test_reasignar_cambia_la_sede_solo_a_una_sede_activa(servicio, sedes, uow, reloj):
    usuario = _biblio(servicio, sedes)

    movido = servicio.modificar(ADMIN, usuario.id, "Lucía G.", sedes["norte"].id)
    assert (movido.nombre, movido.sede.codigo) == ("Lucía G.", "NORTE")
    assert (
        uow.usuarios.obtener(usuario.id).sede_id == sedes["norte"].id
    )  # rige en la siguiente lectura

    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, sedes["centro"].id, 1, "Cierre temporal"
    )
    with pytest.raises(SedeEnBaja):
        servicio.modificar(ADMIN, usuario.id, "Lucía G.", sedes["centro"].id)
    assert uow.usuarios.obtener(usuario.id).sede_id == sedes["norte"].id


def test_modificar_exige_sede_a_un_bibliotecario_y_la_prohibe_a_un_admin(servicio, sedes):
    biblio = _biblio(servicio, sedes)
    admin = servicio.crear(ADMIN, _nuevo(username="otro.admin", rol=Rol.ADMIN))

    with pytest.raises(ErrorDeValidacion):
        servicio.modificar(ADMIN, biblio.id, "Nombre nuevo", None)
    with pytest.raises(ErrorDeValidacion):
        servicio.modificar(ADMIN, admin.id, "Nombre nuevo", sedes["centro"].id)
    assert servicio.modificar(ADMIN, admin.id, "Nombre nuevo", None).nombre == "Nombre nuevo"


def test_editar_el_nombre_no_revalida_la_sede_si_no_cambia(servicio, sedes, uow, reloj):
    usuario = _biblio(servicio, sedes)
    servicio.dar_de_baja(ADMIN, usuario.id)
    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, sedes["centro"].id, 1, "Cierre temporal"
    )

    editado = servicio.modificar(ADMIN, usuario.id, "Lucía Gómez Ruiz", sedes["centro"].id)

    assert editado.nombre == "Lucía Gómez Ruiz" and not editado.activo


@pytest.mark.ca("CA-ACC-10")
def test_la_baja_desvincula_al_bibliotecario_de_la_sede(servicio, sedes, uow):
    usuario = _biblio(servicio, sedes)
    assert uow.usuarios.bibliotecarios_activos_de_sede(sedes["centro"].id, 10)[1] == 1

    baja = servicio.dar_de_baja(ADMIN, usuario.id)

    assert not baja.activo and baja.actualizado_por.id == 100
    assert uow.usuarios.bibliotecarios_activos_de_sede(sedes["centro"].id, 10)[1] == 0
    with pytest.raises(UsuarioYaEnBaja):
        servicio.dar_de_baja(ADMIN, usuario.id)


@pytest.mark.ca("CA-ACC-14")
def test_el_administrador_no_puede_darse_de_baja_a_si_mismo(servicio, uow):
    uow.usuarios.agregar(ADMIN)

    with pytest.raises(ErrorDeValidacion):
        servicio.dar_de_baja(ADMIN, ADMIN.id)

    assert uow.usuarios.obtener(ADMIN.id).activo
    assert uow.reversiones == 1


@pytest.mark.ca("CA-ACC-09")
def test_reactivar_exige_que_la_sede_este_activa(servicio, sedes, uow, reloj):
    usuario = _biblio(servicio, sedes)
    servicio.dar_de_baja(ADMIN, usuario.id)
    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, sedes["centro"].id, 1, "Cierre temporal"
    )

    with pytest.raises(SedeEnBaja):
        servicio.reactivar(ADMIN, usuario.id)
    assert not uow.usuarios.obtener(usuario.id).activo

    servicio.modificar(ADMIN, usuario.id, usuario.nombre, sedes["norte"].id)
    assert servicio.reactivar(ADMIN, usuario.id).activo
    with pytest.raises(UsuarioYaActivo):
        servicio.reactivar(ADMIN, usuario.id)


def test_un_administrador_se_reactiva_sin_sede(servicio, sedes):
    admin = servicio.crear(ADMIN, _nuevo(username="otro.admin", rol=Rol.ADMIN))
    servicio.dar_de_baja(ADMIN, admin.id)

    assert servicio.reactivar(ADMIN, admin.id).activo


def test_un_socio_o_un_id_inexistente_no_son_personal(servicio, uow):
    socio = uow.usuarios.agregar(SocioUsuarioFactory(id=None, username="socio.uno"))

    for accion in (
        lambda: servicio.obtener(ADMIN, socio.id),
        lambda: servicio.modificar(ADMIN, socio.id, "Nombre", None),
        lambda: servicio.dar_de_baja(ADMIN, socio.id),
        lambda: servicio.reactivar(ADMIN, socio.id),
        lambda: servicio.obtener(ADMIN, 999),
    ):
        with pytest.raises(UsuarioNoEncontrado):
            accion()


def test_el_listado_filtra_pagina_y_excluye_socios(servicio, sedes, uow):
    uow.usuarios.agregar(SocioUsuarioFactory(id=None, username="socio.uno"))
    _biblio(servicio, sedes, username="ana.centro", nombre="Ana Centro")
    _biblio(servicio, sedes, sede="norte", username="beto.norte", nombre="Beto Norte")
    baja = _biblio(servicio, sedes, username="carla.centro", nombre="Carla Centro")
    servicio.dar_de_baja(ADMIN, baja.id)
    servicio.crear(ADMIN, _nuevo(username="dina.admin", nombre="Dina Admin", rol=Rol.ADMIN))

    def nombres(**filtros):
        base = {"rol": None, "sede_id": None, "activo": None, "texto": None, "page": 1, "size": 20}
        pagina = servicio.listar(ADMIN, **{**base, **filtros})
        return [u.nombre for u in pagina.items], pagina.total

    assert nombres()[1] == 4  # sin el socio
    assert nombres(rol=Rol.ADMIN) == (["Dina Admin"], 1)
    assert nombres(sede_id=sedes["centro"].id)[0] == ["Ana Centro", "Carla Centro"]
    assert nombres(activo=False) == (["Carla Centro"], 1)
    assert nombres(texto="BETO") == (["Beto Norte"], 1)
    assert nombres(size=2, page=2) == (["Carla Centro", "Dina Admin"], 4)
