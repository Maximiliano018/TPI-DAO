"""Invariantes que garantiza la base de datos (ARCHITECTURE.md §5.2).

Son la red de seguridad del dominio: cada test prueba el caso inválido y, cuando
la regla tiene matices, también el caso válido.
"""

from datetime import date
from typing import Any, NamedTuple

import pytest
from sqlalchemy import insert, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

from biblioteca.domain.enums import (
    EstadoEjemplar,
    EstadoPrestamo,
    EstadoRemito,
    EstadoReserva,
    MotivoBaja,
    MotivoCancelacion,
    ResultadoRevision,
    Rol,
    Sentido,
    TipoNotificacion,
)
from biblioteca.infrastructure.db import tables as t
from tests import datos
from tests.datos import AHORA, HOY


class Escenario(NamedTuple):
    sede_a: int
    sede_b: int
    usuario: int
    libro: int
    ejemplar: int
    socio: int


@pytest.fixture
def esc(engine: Engine) -> Escenario:
    with engine.begin() as conn:
        sede_a = datos.sede(conn)
        sede_b = datos.sede(conn)
        libro = datos.libro(conn)
        return Escenario(
            sede_a=sede_a,
            sede_b=sede_b,
            usuario=datos.usuario(conn, sede_a),
            libro=libro,
            ejemplar=datos.ejemplar(conn, libro, sede_a),
            socio=datos.socio(conn),
        )


def _prestamo_local(conn: Connection, esc: Escenario, **campos: Any) -> int:
    return datos.prestamo(
        conn,
        socio_id=esc.socio,
        ejemplar_id=esc.ejemplar,
        sede_origen_id=esc.sede_a,
        sede_destino_id=esc.sede_a,
        registrado_por=esc.usuario,
        **campos,
    )


def _remito(conn: Connection, esc: Escenario, **campos: Any) -> int:
    return datos.remito(
        conn,
        ejemplar_id=esc.ejemplar,
        sede_origen_id=esc.sede_a,
        sede_destino_id=esc.sede_b,
        **campos,
    )


# ------------------------------------------------------------------------- Generales


def test_las_claves_foraneas_se_controlan(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), engine.begin() as conn:
        datos.ejemplar(conn, esc.libro, sede_id=9999)


def test_no_admite_valores_fuera_de_la_enumeracion(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="ck_ejemplar_estado_valido"), engine.begin() as conn:
        datos.ejemplar(conn, esc.libro, esc.sede_a, estado="PERDIDO")


@pytest.mark.parametrize(
    ("tabla", "campos"),
    [
        ("socio", {"dni": "DUP"}),
        ("libro", {"isbn": "9780000000001"}),
        ("sede", {"codigo": "DUP"}),
    ],
)
def test_evita_duplicados(engine: Engine, tabla: str, campos: dict[str, str]) -> None:
    crear = {"socio": datos.socio, "libro": datos.libro, "sede": datos.sede}[tabla]
    with engine.begin() as conn:
        crear(conn, **campos)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        crear(conn, **campos)


# ---------------------------------------------------------------- Sedes y usuarios


def test_una_sede_dada_de_baja_requiere_fecha(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="ck_sede_baja_con_fecha"), engine.begin() as conn:
        datos.sede(conn, activa=False)


def test_solo_el_admin_no_tiene_sede(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="admin_sin_sede"), engine.begin() as conn:
        datos.usuario(conn, esc.sede_a, rol=Rol.ADMIN)
    with pytest.raises(IntegrityError, match="admin_sin_sede"), engine.begin() as conn:
        datos.usuario(conn, None, rol=Rol.LOGISTICA)
    with engine.begin() as conn:
        datos.usuario(conn, None, rol=Rol.ADMIN)


def test_un_socio_inhabilitado_requiere_motivo(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="inhabilitacion_con_motivo"), engine.begin() as conn:
        datos.socio(conn, habilitado=False)


# -------------------------------------------------------------------------- Ejemplar


def test_la_baja_de_un_ejemplar_requiere_motivo_y_fecha(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="baja_con_motivo"), engine.begin() as conn:
        datos.ejemplar(conn, esc.libro, esc.sede_a, estado=EstadoEjemplar.BAJA, fecha_baja=HOY)
    with engine.begin() as conn:
        datos.ejemplar(
            conn,
            esc.libro,
            esc.sede_a,
            estado=EstadoEjemplar.BAJA,
            fecha_baja=HOY,
            motivo_baja=MotivoBaja.EXTRAVIO,
        )


# -------------------------------------------------------------------------- Préstamo


def test_un_ejemplar_tiene_un_solo_prestamo_abierto(engine: Engine, esc: Escenario) -> None:
    with engine.begin() as conn:
        _prestamo_local(conn, esc)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        _prestamo_local(conn, esc)


def test_un_ejemplar_devuelto_puede_volver_a_prestarse(engine: Engine, esc: Escenario) -> None:
    with engine.begin() as conn:
        _prestamo_local(conn, esc, estado=EstadoPrestamo.DEVUELTO, fecha_cierre=AHORA)
        _prestamo_local(conn, esc)


def test_un_prestamo_en_envio_debe_ser_entre_sedes_distintas(
    engine: Engine, esc: Escenario
) -> None:
    with pytest.raises(IntegrityError, match="envio_entre_sedes_distintas"), engine.begin() as conn:
        _prestamo_local(
            conn, esc, estado=EstadoPrestamo.EN_ENVIO, fecha_inicio=None, fecha_vencimiento=None
        )


def test_un_prestamo_activo_requiere_inicio_y_vencimiento(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="entregado_con_fechas"), engine.begin() as conn:
        _prestamo_local(conn, esc, fecha_vencimiento=None)


def test_el_vencimiento_no_puede_ser_anterior_al_inicio(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="vencimiento_posterior"), engine.begin() as conn:
        _prestamo_local(conn, esc, fecha_vencimiento=date(2026, 10, 1))


def test_un_prestamo_cancelado_requiere_motivo(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="cancelado_con_motivo"), engine.begin() as conn:
        _prestamo_local(conn, esc, estado=EstadoPrestamo.CANCELADO, fecha_cierre=AHORA)
    with engine.begin() as conn:
        _prestamo_local(
            conn,
            esc,
            estado=EstadoPrestamo.CANCELADO,
            fecha_cierre=AHORA,
            motivo_cancelacion=MotivoCancelacion.DESISTIDO,
        )


# ---------------------------------------------------------------------------- Remito


def test_un_remito_no_va_de_una_sede_a_si_misma(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="sedes_distintas"), engine.begin() as conn:
        datos.remito(
            conn, ejemplar_id=esc.ejemplar, sede_origen_id=esc.sede_a, sede_destino_id=esc.sede_a
        )


def test_un_ejemplar_tiene_un_solo_remito_no_finalizado(engine: Engine, esc: Escenario) -> None:
    with engine.begin() as conn:
        _remito(conn, esc)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        _remito(conn, esc)


def test_una_vuelta_cancelada_se_puede_reemplazar(engine: Engine, esc: Escenario) -> None:
    with engine.begin() as conn:
        prestamo_id = _prestamo_local(conn, esc, estado=EstadoPrestamo.DEVUELTO, fecha_cierre=AHORA)
        _remito(
            conn,
            esc,
            prestamo_id=prestamo_id,
            sentido=Sentido.VUELTA,
            estado=EstadoRemito.CANCELADO,
        )
        _remito(conn, esc, prestamo_id=prestamo_id, sentido=Sentido.VUELTA)
    # Una segunda vuelta vigente para el mismo préstamo no se admite.
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        conn.execute(
            update(t.remito)
            .where(t.remito.c.estado == EstadoRemito.GENERADO)
            .values(
                estado=EstadoRemito.RECIBIDO,
                fecha_despacho=AHORA,
                fecha_recepcion=AHORA,
                resultado_revision=ResultadoRevision.CONFORME,
            )
        )
        _remito(conn, esc, prestamo_id=prestamo_id, sentido=Sentido.VUELTA)


def test_un_remito_recibido_requiere_revision(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="recibido_con_revision"), engine.begin() as conn:
        _remito(
            conn, esc, estado=EstadoRemito.RECIBIDO, fecha_despacho=AHORA, fecha_recepcion=AHORA
        )


def test_un_remito_despachado_requiere_fecha_de_despacho(engine: Engine, esc: Escenario) -> None:
    with pytest.raises(IntegrityError, match="despachado_con_fecha"), engine.begin() as conn:
        _remito(conn, esc, estado=EstadoRemito.EN_TRANSITO)


# --------------------------------------------------------------------------- Reserva


def test_un_socio_tiene_una_reserva_abierta_por_libro(engine: Engine, esc: Escenario) -> None:
    def reservar(conn: Connection) -> int:
        return datos.reserva(
            conn,
            socio_id=esc.socio,
            libro_id=esc.libro,
            sede_id=esc.sede_a,
            registrado_por=esc.usuario,
        )

    with engine.begin() as conn:
        reservar(conn)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        reservar(conn)


def test_una_reserva_asignada_requiere_ejemplar_y_fecha_limite(
    engine: Engine, esc: Escenario
) -> None:
    with pytest.raises(IntegrityError, match="asignada_con"), engine.begin() as conn:
        datos.reserva(
            conn,
            socio_id=esc.socio,
            libro_id=esc.libro,
            sede_id=esc.sede_a,
            registrado_por=esc.usuario,
            estado=EstadoReserva.ASIGNADA,
            ejemplar_asignado_id=esc.ejemplar,
            fecha_asignacion=AHORA,
        )


def test_un_ejemplar_se_aparta_para_una_sola_reserva(engine: Engine, esc: Escenario) -> None:
    def asignar(conn: Connection, socio_id: int) -> int:
        return datos.reserva(
            conn,
            socio_id=socio_id,
            libro_id=esc.libro,
            sede_id=esc.sede_a,
            registrado_por=esc.usuario,
            estado=EstadoReserva.ASIGNADA,
            ejemplar_asignado_id=esc.ejemplar,
            fecha_asignacion=AHORA,
            fecha_limite=HOY,
        )

    with engine.begin() as conn:
        asignar(conn, esc.socio)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        asignar(conn, datos.socio(conn))


# ----------------------------------------------------------------------- Notificación


def test_un_aviso_de_vencimiento_por_prestamo(engine: Engine, esc: Escenario) -> None:
    with engine.begin() as conn:
        prestamo_id = _prestamo_local(conn, esc)

    def avisar(conn: Connection) -> None:
        conn.execute(
            insert(t.notificacion).values(
                socio_id=esc.socio,
                tipo=TipoNotificacion.VENCIMIENTO_PROXIMO,
                prestamo_id=prestamo_id,
                mensaje="Su préstamo vence pronto",
                fecha_hora=AHORA,
            )
        )

    with engine.begin() as conn:
        avisar(conn)
    with pytest.raises(IntegrityError, match="UNIQUE"), engine.begin() as conn:
        avisar(conn)
