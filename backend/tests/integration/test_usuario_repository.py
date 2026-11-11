"""Repositorio de usuarios contra PostgreSQL."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.exceptions import DuplicadoError
from app.models.usuario import Rol, SedeRef, Usuario, UsuarioRef
from app.repositories.impl.usuario_repository import SqlAlchemyUsuarioRepository
from app.repositories.interfaces.usuario_repository import FiltroUsuarios
from tests.factories.datos_orm import crear_admin, crear_sede

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


@pytest.fixture
def mundo(sesion: Session):
    admin = crear_admin(sesion, nombre="Ana Admin")
    sede = crear_sede(sesion, admin, codigo="CEN")
    return {"admin": admin, "sede": sede, "repo": SqlAlchemyUsuarioRepository(sesion)}


def _nuevo(mundo, username="lucia.gomez", rol=Rol.BIBLIOTECARIO, nombre="Lucía Gómez") -> Usuario:
    sede = mundo["sede"]
    admin = mundo["admin"]
    return Usuario.crear_personal(
        username=username,
        nombre=nombre,
        rol=rol,
        sede=SedeRef(sede.id, sede.codigo, sede.nombre) if rol == Rol.BIBLIOTECARIO else None,
        password_hash="hash",
        actor=UsuarioRef(admin.id, admin.nombre),
        ahora=AHORA,
    )


def test_agregar_asigna_id_y_el_detalle_trae_los_nombres_de_auditoria(mundo):
    usuario = _nuevo(mundo)

    mundo["repo"].agregar(usuario)
    leido = mundo["repo"].obtener_detalle(usuario.id)

    assert usuario.id and leido.username == "lucia.gomez" and leido.sede.codigo == "CEN"
    assert leido.creado_por == UsuarioRef(mundo["admin"].id, "Ana Admin")
    assert leido.actualizado_en == AHORA and leido.password_hash == "hash"
    assert (
        mundo["repo"].obtener(usuario.id).creado_por is None
    )  # el camino de auth no resuelve nombres


def test_un_username_repetido_lo_rechaza_la_base_y_la_sesion_sigue_usable(mundo):
    mundo["repo"].agregar(_nuevo(mundo))

    with pytest.raises(DuplicadoError):
        mundo["repo"].agregar(_nuevo(mundo))

    assert mundo["repo"].obtener_por_username("lucia.gomez") is not None


def test_guardar_persiste_nombre_sede_estado_y_auditoria(mundo, sesion):
    usuario = _nuevo(mundo)
    mundo["repo"].agregar(usuario)
    otra = crear_sede(sesion, mundo["admin"], codigo="NORTE")
    otro_admin = crear_admin(sesion, nombre="Otro Admin")

    modificable = mundo["repo"].obtener_para_modificar(usuario.id)
    modificable.modificar(
        nombre="Lucía G.",
        sede=SedeRef(otra.id, otra.codigo, otra.nombre),
        actor=UsuarioRef(otro_admin.id, otro_admin.nombre),
        ahora=datetime(2026, 11, 11, tzinfo=UTC),
    )
    modificable.dar_de_baja(actor=UsuarioRef(otro_admin.id, otro_admin.nombre), ahora=AHORA)
    mundo["repo"].guardar(modificable)

    leido = mundo["repo"].obtener_detalle(usuario.id)
    assert (leido.nombre, leido.sede.codigo, leido.activo) == ("Lucía G.", "NORTE", False)
    assert leido.actualizado_por.nombre == "Otro Admin" and leido.creado_por.nombre == "Ana Admin"


def test_listar_filtra_ordena_y_pagina_solo_personal(mundo, sesion):
    for username, nombre, rol in [
        ("zoe.admin", "Zoe Admin", Rol.ADMIN),
        ("ana.biblio", "Ánge Biblio", Rol.BIBLIOTECARIO),
        ("beto.biblio", "Beto Biblio", Rol.BIBLIOTECARIO),
    ]:
        mundo["repo"].agregar(_nuevo(mundo, username, rol, nombre))
    repo = mundo["repo"]

    todos, total = repo.listar(FiltroUsuarios(), 1, 10)
    assert total == 4 and [u.nombre for u in todos] == [
        "Ana Admin",
        "Ánge Biblio",
        "Beto Biblio",
        "Zoe Admin",
    ]
    assert [u.username for u in repo.listar(FiltroUsuarios(rol=Rol.BIBLIOTECARIO), 1, 10)[0]] == [
        "ana.biblio",
        "beto.biblio",
    ]
    assert [u.username for u in repo.listar(FiltroUsuarios(texto="ange"), 1, 10)[0]] == [
        "ana.biblio"
    ]
    assert [u.username for u in repo.listar(FiltroUsuarios(texto="beto.b"), 1, 10)[0]] == [
        "beto.biblio"
    ]
    assert repo.listar(FiltroUsuarios(texto="100%"), 1, 10)[1] == 0
    assert repo.listar(FiltroUsuarios(sede_id=mundo["sede"].id), 1, 10)[1] == 2
    assert repo.listar(FiltroUsuarios(activo=False), 1, 10)[1] == 0
    assert len(repo.listar(FiltroUsuarios(), 2, 3)[0]) == 1


def test_bibliotecarios_activos_de_sede_cuenta_todos_y_limita_la_muestra(mundo):
    repo = mundo["repo"]
    for n in range(3):
        repo.agregar(_nuevo(mundo, f"biblio{n}", nombre=f"Biblio {n}"))
    inactivo = _nuevo(mundo, "biblio.baja", nombre="Biblio Baja")
    repo.agregar(inactivo)
    inactivo.dar_de_baja(actor=UsuarioRef(mundo["admin"].id, "Ana Admin"), ahora=AHORA)
    repo.guardar(inactivo)

    muestra, total = repo.bibliotecarios_activos_de_sede(mundo["sede"].id, 2)

    assert total == 3 and [u.username for u in muestra] == ["biblio0", "biblio1"]
    assert repo.bibliotecarios_activos_de_sede(999_999, 10) == ([], 0)
