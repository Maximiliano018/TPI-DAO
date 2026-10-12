"""La circulación de demostración respeta las máquinas de estado (ARCHITECTURE.md §4.4)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from biblioteca.domain.enums import (
    EstadoEjemplar,
    EstadoPrestamo,
    EstadoRemito,
    EstadoReserva,
)
from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.db.seed import cargar_datos_iniciales, cargar_demo


@pytest.fixture
def conn(engine: Engine) -> Iterator[Connection]:
    with engine.begin() as c:
        cargar_datos_iniciales(c)
        cargar_demo(c)
    with engine.connect() as c:
        yield c


def _estado_ejemplares(conn: Connection) -> dict[int, str]:
    return {i: e for i, e in conn.execute(select(t.ejemplar.c.id, t.ejemplar.c.estado))}


def test_ejemplar_con_remito_abierto_esta_comprometido_o_viajando(conn: Connection) -> None:
    estados = _estado_ejemplares(conn)
    esperado = {
        EstadoRemito.GENERADO: EstadoEjemplar.PENDIENTE_DESPACHO,
        EstadoRemito.EMPAQUETADO: EstadoEjemplar.PENDIENTE_DESPACHO,
        EstadoRemito.EN_TRANSITO: EstadoEjemplar.EN_TRANSITO,
    }
    abiertos = conn.execute(
        select(t.remito.c.ejemplar_id, t.remito.c.estado).where(
            t.remito.c.estado.in_(list(esperado))
        )
    ).all()

    assert abiertos
    for ejemplar_id, estado_remito in abiertos:
        assert estados[ejemplar_id] == esperado[EstadoRemito(estado_remito)]


def test_ejemplar_prestado_tiene_prestamo_activo(conn: Connection) -> None:
    prestados = {i for i, e in _estado_ejemplares(conn).items() if e == EstadoEjemplar.PRESTADO}
    con_prestamo_activo = set(
        conn.execute(
            select(t.prestamo.c.ejemplar_id).where(t.prestamo.c.estado == EstadoPrestamo.ACTIVO)
        ).scalars()
    )
    assert prestados and prestados == con_prestamo_activo


def test_ejemplar_reservado_espera_a_un_socio(conn: Connection) -> None:
    reservados = {i for i, e in _estado_ejemplares(conn).items() if e == EstadoEjemplar.RESERVADO}
    listos = set(
        conn.execute(
            select(t.prestamo.c.ejemplar_id).where(
                t.prestamo.c.estado == EstadoPrestamo.LISTO_PARA_RETIRO
            )
        ).scalars()
    )
    asignados = set(
        conn.execute(
            select(t.reserva.c.ejemplar_asignado_id).where(
                t.reserva.c.estado == EstadoReserva.ASIGNADA
            )
        ).scalars()
    )
    assert reservados and reservados == listos | asignados


def test_movimientos_de_cada_remito_forman_una_cadena_sin_saltos(conn: Connection) -> None:
    remitos = conn.execute(select(t.remito.c.id, t.remito.c.estado)).all()
    assert remitos
    for remito_id, estado_final in remitos:
        movimientos = conn.execute(
            select(t.movimiento_remito.c.estado_anterior, t.movimiento_remito.c.estado_nuevo)
            .where(t.movimiento_remito.c.remito_id == remito_id)
            .order_by(t.movimiento_remito.c.fecha_hora)
        ).all()
        anterior = None
        for estado_anterior, estado_nuevo in movimientos:
            assert estado_anterior == anterior
            anterior = estado_nuevo
        assert movimientos[0].estado_nuevo == EstadoRemito.GENERADO
        assert anterior == estado_final
