"""Mapeo imperativo, repositorios y Unidad de Trabajo contra una base real."""

from datetime import time

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine

from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.entities.usuario import Usuario
from biblioteca.domain.enums import EstadoPrestamo, Rol
from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests import datos
from tests.datos import AHORA


def _guardar_sede(uow: SqlAlchemyUnitOfWork, codigo: str = "CEN") -> int:
    sede = Sede(codigo, f"Sede {codigo}", "Calle 1", "Córdoba")
    sede.definir_horarios([HorarioSede(1, time(8), time(12)), HorarioSede(1, time(16), time(20))])
    with uow:
        uow.sedes.agregar(sede)
        uow.commit()
    assert sede.id is not None
    return sede.id


def test_la_sede_se_guarda_y_se_recupera_con_sus_horarios(uow: SqlAlchemyUnitOfWork) -> None:
    sede_id = _guardar_sede(uow)

    with uow:
        sede = uow.sedes.obtener(sede_id)
    assert sede is not None
    assert sede.codigo == "CEN"
    assert sede.activa is True
    assert [(h.dia_semana, h.hora_apertura) for h in sede.horarios] == [
        (1, time(8)),
        (1, time(16)),
    ]


def test_redefinir_horarios_borra_las_franjas_anteriores(
    uow: SqlAlchemyUnitOfWork, engine: Engine
) -> None:
    sede_id = _guardar_sede(uow)
    with uow:
        sede = uow.sedes.obtener(sede_id)
        assert sede is not None
        sede.definir_horarios([HorarioSede(6, time(9), time(13))])
        uow.commit()

    with engine.connect() as conn:
        filas = conn.execute(select(t.horario_sede.c.dia_semana)).scalars().all()
    assert filas == [6]


def test_sin_commit_los_cambios_se_descartan(uow: SqlAlchemyUnitOfWork) -> None:
    with uow:
        uow.sedes.agregar(Sede("CEN", "Sede Central", "Calle 1", "Córdoba"))
    with uow:
        assert uow.sedes.contar(solo_activas=False) == 0


def test_una_excepcion_revierte_la_transaccion(uow: SqlAlchemyUnitOfWork) -> None:
    with pytest.raises(RuntimeError), uow:
        uow.sedes.agregar(Sede("CEN", "Sede Central", "Calle 1", "Córdoba"))
        uow.session.flush()
        raise RuntimeError("falla a mitad del caso de uso")
    with uow:
        assert uow.sedes.contar(solo_activas=False) == 0


def test_las_enumeraciones_vuelven_como_enum(uow: SqlAlchemyUnitOfWork) -> None:
    sede_id = _guardar_sede(uow)
    with uow:
        uow.usuarios.agregar(Usuario("ana", "Ana Pérez", "hash", Rol.BIBLIOTECARIO, sede_id))
        uow.commit()
    with uow:
        usuario = uow.usuarios.obtener_por_username("ana")
    assert usuario is not None
    assert usuario.rol is Rol.BIBLIOTECARIO


def test_la_base_registra_la_fecha_de_actualizacion(
    uow: SqlAlchemyUnitOfWork, engine: Engine
) -> None:
    sede_id = _guardar_sede(uow)
    # Se fuerza una fecha vieja para no depender de la resolución de CURRENT_TIMESTAMP.
    with engine.begin() as conn:
        conn.execute(update(t.sede).values(actualizado_en=AHORA.replace(year=2000)))
    with uow:
        sede = uow.sedes.obtener(sede_id)
        assert sede is not None
        sede.actualizar_datos("Nuevo nombre", "Calle 2", "Córdoba", None, None)
        uow.commit()
    with engine.connect() as conn:
        actualizado = conn.execute(select(t.sede.c.actualizado_en)).scalar_one()
    assert actualizado.year > 2000


def test_listar_ordena_por_nombre_y_pagina(uow: SqlAlchemyUnitOfWork) -> None:
    for codigo in ("SUR", "CEN", "NOR"):
        _guardar_sede(uow, codigo)
    with uow:
        pagina = uow.sedes.listar(solo_activas=False, limite=2, desde=1)
    assert [s.codigo for s in pagina] == ["NOR", "SUR"]


def test_existe_nombre_ignora_mayusculas(uow: SqlAlchemyUnitOfWork) -> None:
    sede_id = _guardar_sede(uow)
    with uow:
        assert uow.sedes.existe_nombre("SEDE cen")
        assert not uow.sedes.existe_nombre("SEDE cen", excepto_id=sede_id)


def test_actividad_abierta_considera_prestamos_en_curso(
    uow: SqlAlchemyUnitOfWork, engine: Engine
) -> None:
    with engine.begin() as conn:
        sede_id = datos.sede(conn)
        libro_id = datos.libro(conn)
        prestamo_id = datos.prestamo(
            conn,
            socio_id=datos.socio(conn),
            ejemplar_id=datos.ejemplar(conn, libro_id, sede_id),
            sede_origen_id=sede_id,
            sede_destino_id=sede_id,
            registrado_por=datos.usuario(conn, sede_id),
        )
    with uow:
        assert uow.sedes.tiene_actividad_abierta(sede_id)

    with engine.begin() as conn:
        conn.execute(
            update(t.prestamo)
            .where(t.prestamo.c.id == prestamo_id)
            .values(estado=EstadoPrestamo.DEVUELTO, fecha_cierre=AHORA)
        )
    with uow:
        assert not uow.sedes.tiene_actividad_abierta(sede_id)


def test_contar_respeta_el_filtro_de_activas(uow: SqlAlchemyUnitOfWork, engine: Engine) -> None:
    _guardar_sede(uow, "CEN")
    _guardar_sede(uow, "NOR")
    with engine.begin() as conn:
        conn.execute(
            update(t.sede).where(t.sede.c.codigo == "NOR").values(activa=False, fecha_baja=AHORA)
        )
    with uow:
        assert uow.sedes.contar(solo_activas=True) == 1
        assert uow.sedes.contar(solo_activas=False) == 2
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.sede)).scalar_one() == 2
