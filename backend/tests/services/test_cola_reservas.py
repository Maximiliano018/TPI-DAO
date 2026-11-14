"""Cola de reservas: cancelación de las reservas de un libro que se quedó sin ejemplares."""

import pytest

from app.models.ejemplar import Ejemplar, EstadoFisico
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum as R
from app.models.usuario import UsuarioRef
from app.services.cola_reservas import MOTIVO_SIN_EJEMPLARES, ColaDeReservas
from tests.fakes.repositorios import UnitOfWorkEnMemoria

LIBRO = 12
ACTOR = UsuarioRef(1, "Ana Admin")


@pytest.fixture
def uow(reloj) -> UnitOfWorkEnMemoria:
    uow = UnitOfWorkEnMemoria()
    for i in (1, 2):
        uow.reservas.reservas[i] = Reserva(
            id=i,
            numero=f"RS-2026-00000{i}",
            socio_id=40 + i,
            libro_id=LIBRO,
            sede_retiro_id=2,
            fecha_reserva=reloj.ahora(),
        )
    return uow


def _estados(uow: UnitOfWorkEnMemoria) -> list[R]:
    return [r.estado_nombre for r in uow.reservas.reservas.values()]


@pytest.mark.ca("CA-RES-21")
def test_sin_ejemplares_activos_las_pendientes_se_cancelan_a_nombre_del_sistema(uow, reloj):
    reservas = list(uow.reservas.reservas.values())
    historiales = []
    original = uow.reservas.guardar

    def guardar(reserva: Reserva) -> None:
        historiales.extend(reserva.movimientos_pendientes)
        original(reserva)

    uow.reservas.guardar = guardar  # type: ignore[method-assign]

    canceladas = ColaDeReservas(uow, reloj).revisar_libro(LIBRO)

    assert canceladas == 2
    assert _estados(uow) == [R.CANCELADA, R.CANCELADA]
    assert all(r.fecha_cierre == reloj.ahora() for r in reservas)
    assert [(m.usuario, m.observacion) for m in historiales] == [
        (None, MOTIVO_SIN_EJEMPLARES),
        (None, MOTIVO_SIN_EJEMPLARES),
    ]


@pytest.mark.ca("CA-RES-21")
def test_con_un_extravio_pendiente_las_reservas_siguen_esperando(uow, reloj):
    uow.incidencias.libros_con_extravio.add(LIBRO)  # el ejemplar puede aparecer y recuperarse

    assert ColaDeReservas(uow, reloj).revisar_libro(LIBRO) == 0
    assert _estados(uow) == [R.PENDIENTE, R.PENDIENTE]


def test_con_ejemplares_activos_no_cancela(uow, reloj):
    uow.ejemplares.agregar(
        Ejemplar.registrar(
            codigo_inventario="CEN-1",
            libro_id=LIBRO,
            sede_id=1,
            estado_fisico=EstadoFisico.BUENO,
            observaciones=None,
            actor=ACTOR,
            ahora=reloj.ahora(),
        )
    )

    assert ColaDeReservas(uow, reloj).revisar_libro(LIBRO) == 0
    assert _estados(uow) == [R.PENDIENTE, R.PENDIENTE]
