from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import insert, select, text
from sqlalchemy.engine import Engine

from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.db.migraciones import configuracion_alembic


def test_las_migraciones_coinciden_con_el_esquema(base_migrada: Path) -> None:
    # Falla si alguien cambia tables.py sin generar la migración correspondiente.
    command.check(configuracion_alembic(f"sqlite:///{base_migrada}"))


def test_la_migracion_se_puede_revertir_y_reaplicar(tmp_path: Path) -> None:
    config = configuracion_alembic(f"sqlite:///{tmp_path / 'ida_y_vuelta.db'}")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_cada_conexion_activa_los_pragmas_de_sqlite(engine: Engine) -> None:
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000


def test_las_fechas_se_guardan_en_utc_y_vuelven_con_zona(engine: Engine) -> None:
    hora_argentina = datetime(2026, 10, 12, 12, 0, tzinfo=timezone(timedelta(hours=-3)))
    with engine.begin() as conn:
        conn.execute(
            insert(t.sede).values(
                codigo="CEN",
                nombre="Central",
                direccion="Calle 1",
                localidad="Córdoba",
                activa=False,
                fecha_baja=hora_argentina,
            )
        )
        guardada = conn.execute(select(t.sede.c.fecha_baja)).scalar_one()

    assert guardada == datetime(2026, 10, 12, 15, 0, tzinfo=UTC)


def test_rechaza_fechas_sin_zona_horaria(engine: Engine) -> None:
    with pytest.raises(Exception, match="zona horaria"), engine.begin() as conn:
        conn.execute(
            insert(t.sede).values(
                codigo="CEN",
                nombre="Central",
                direccion="Calle 1",
                localidad="Córdoba",
                activa=False,
                fecha_baja=datetime(2026, 10, 12, 12, 0),
            )
        )
