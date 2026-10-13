"""Mapeo imperativo, repositorios de sedes y usuarios, y unidad de trabajo contra una base real."""

from collections.abc import Callable
from datetime import time

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.entities.usuario import Usuario
from biblioteca.domain.enums import EstadoPrestamo, Rol
from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.repositories.unidad_de_trabajo import SqlUnidadDeTrabajo
from tests import datos
from tests.datos import AHORA

NuevaUow = Callable[[], SqlUnidadDeTrabajo]


def _guardar_sede(nueva_uow: NuevaUow, codigo: str = "CEN") -> int:
    sede = Sede(codigo, f"Sede {codigo}", "Calle 1", "Córdoba")
    sede.definir_horarios([HorarioSede(1, time(8), time(12)), HorarioSede(1, time(16), time(20))])
    uow = nueva_uow()
    uow.sedes.agregar(sede)
    uow.confirmar()
    assert sede.id is not None
    return sede.id


def test_la_sede_se_guarda_y_se_recupera_con_sus_horarios(nueva_uow: NuevaUow) -> None:
    sede_id = _guardar_sede(nueva_uow)

    sede = nueva_uow().sedes.obtener(sede_id)
    assert sede is not None
    assert sede.codigo == "CEN"
    assert sede.activa is True
    assert [(h.dia_semana, h.hora_apertura) for h in sede.horarios] == [
        (1, time(8)),
        (1, time(16)),
    ]


def test_redefinir_horarios_borra_las_franjas_anteriores(
    nueva_uow: NuevaUow, engine: Engine
) -> None:
    sede_id = _guardar_sede(nueva_uow)
    uow = nueva_uow()
    sede = uow.sedes.obtener(sede_id)
    assert sede is not None
    sede.definir_horarios([HorarioSede(6, time(9), time(13))])
    uow.confirmar()

    with engine.connect() as conn:
        filas = conn.execute(select(t.horario_sede.c.dia_semana)).scalars().all()
    assert filas == [6]


def test_sin_confirmar_no_se_guarda_nada(nueva_uow: NuevaUow) -> None:
    uow = nueva_uow()
    uow.sedes.agregar(Sede("CEN", "Sede Central", "Calle 1", "Córdoba"))
    uow._session.flush()  # llega a la base dentro de la transacción, pero sin confirmar
    uow._session.close()

    assert not nueva_uow().sedes.existe_codigo("CEN")


def test_las_enumeraciones_vuelven_como_enum(nueva_uow: NuevaUow) -> None:
    sede_id = _guardar_sede(nueva_uow)
    uow = nueva_uow()
    uow.usuarios.agregar(Usuario("ana", "Ana Pérez", "hash", Rol.BIBLIOTECARIO, sede_id))
    uow.confirmar()

    usuario = nueva_uow().usuarios.obtener_por_username("ana")
    assert usuario is not None
    assert usuario.rol is Rol.BIBLIOTECARIO


def test_la_base_registra_la_fecha_de_actualizacion(nueva_uow: NuevaUow, engine: Engine) -> None:
    sede_id = _guardar_sede(nueva_uow)
    # Se fuerza una fecha vieja para no depender de la resolución de CURRENT_TIMESTAMP.
    with engine.begin() as conn:
        conn.execute(update(t.sede).values(actualizado_en=AHORA.replace(year=2000)))

    uow = nueva_uow()
    sede = uow.sedes.obtener(sede_id)
    assert sede is not None
    sede.actualizar_datos("Nuevo nombre", "Calle 2", "Córdoba", None, None)
    uow.confirmar()

    with engine.connect() as conn:
        actualizado = conn.execute(select(t.sede.c.actualizado_en)).scalar_one()
    assert actualizado.year > 2000


def test_existe_nombre_ignora_mayusculas(nueva_uow: NuevaUow) -> None:
    sede_id = _guardar_sede(nueva_uow)
    sedes = nueva_uow().sedes
    assert sedes.existe_nombre("SEDE cen")
    assert not sedes.existe_nombre("SEDE cen", excepto_id=sede_id)


def test_actividad_abierta_considera_prestamos_en_curso(
    nueva_uow: NuevaUow, engine: Engine
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
    assert nueva_uow().sedes.tiene_actividad_abierta(sede_id)

    with engine.begin() as conn:
        conn.execute(
            update(t.prestamo)
            .where(t.prestamo.c.id == prestamo_id)
            .values(estado=EstadoPrestamo.DEVUELTO, fecha_cierre=AHORA)
        )
    assert not nueva_uow().sedes.tiene_actividad_abierta(sede_id)
