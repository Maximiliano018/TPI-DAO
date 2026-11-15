"""Devoluciones y multas contra PostgreSQL: fecha retroactiva con motivo y multa coherente."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_catalogo_repository import _ejemplar
from tests.integration.test_prestamo_repository import _insertar, datos  # noqa: F401

pytestmark = pytest.mark.integration


@pytest.fixture
def prestamo_id(sesion: Session, datos) -> int:  # noqa: F811
    ejemplar = _ejemplar(sesion, datos["actor"], datos["libro"], datos["a"].id, "CEN-1")
    _insertar(
        sesion,
        datos,
        ejemplar.id,
        "DEVUELTO",
        fecha_inicio="2026-11-01",
        fecha_vencimiento="2026-11-15",
        fecha_devolucion="2026-11-20",
    )
    return sesion.scalar(text("SELECT id FROM prestamo"))


def _devolucion(sesion: Session, d, prestamo: int, fecha: str, motivo: str | None) -> None:
    sesion.execute(
        text(
            "INSERT INTO devolucion (prestamo_id, sede_id, fecha_hora, estado_fisico_recibido, "
            "dias_atraso, registrada_por_id, registrada_en, motivo_fecha) VALUES "
            "(:p, :s, CAST(:f AS timestamptz), 'BUENO', 0, :u, now(), :m)"
        ),
        {"p": prestamo, "s": d["a"].id, "f": fecha, "u": d["actor"].id, "m": motivo},
    )


@pytest.mark.ca("CA-DEV-17")
def test_una_devolucion_retroactiva_sin_motivo_es_rechazada(sesion: Session, datos, prestamo_id):  # noqa: F811
    with pytest.raises(IntegrityError, match="ck_devolucion_retroactiva_con_motivo"):
        _devolucion(sesion, datos, prestamo_id, "2026-01-01T10:00:00Z", None)


@pytest.mark.ca("CA-DEV-17")
def test_una_devolucion_retroactiva_con_motivo_es_valida(sesion: Session, datos, prestamo_id):  # noqa: F811
    _devolucion(sesion, datos, prestamo_id, "2026-01-01T10:00:00Z", "Lo dejó en el buzón")


def _multa(sesion: Session, d, prestamo: int, dias: int, por_dia: str, total: str) -> None:
    sesion.execute(
        text(
            "INSERT INTO multa (prestamo_id, socio_id, dias_atraso, monto_por_dia, monto_total, "
            "estado, fecha_generacion) VALUES (:p, :s, :d, :pd, :t, 'PENDIENTE', now())"
        ),
        {"p": prestamo, "s": d["socio"].id, "d": dias, "pd": por_dia, "t": total},
    )


@pytest.mark.ca("CA-DEV-18")
@pytest.mark.parametrize(
    ("dias", "por_dia", "total", "restriccion"),
    [
        (0, "200", "0", "ck_multa_atraso_positivo"),
        (5, "200", "1200", "ck_multa_monto_coherente"),
    ],
)
def test_la_multa_es_coherente_con_su_atraso(
    sesion: Session,
    datos,  # noqa: F811
    prestamo_id,
    dias,
    por_dia,
    total,
    restriccion,
):
    with pytest.raises(IntegrityError, match=restriccion):
        _multa(sesion, datos, prestamo_id, dias, por_dia, total)


@pytest.mark.ca("CA-DEV-18")
def test_una_multa_con_tope_es_valida(sesion: Session, datos, prestamo_id):  # noqa: F811
    _multa(sesion, datos, prestamo_id, 5, "200", "500")
