from sqlalchemy import Table, func, select, update
from sqlalchemy.engine import Engine

from biblioteca.infrastructure.db import tables as t
from biblioteca.infrastructure.db.secuencias import (
    formatear_codigo_inventario,
    formatear_numero_remito,
    siguiente_valor,
)
from biblioteca.infrastructure.db.seed import (
    CATEGORIAS_INICIALES,
    PARAMETROS_INICIALES,
    cargar_datos_iniciales,
    cargar_demo,
    isbn13_con_verificador,
)


def _contar(engine: Engine, tabla: Table) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(tabla)).scalar_one()


def test_las_secuencias_son_independientes_y_correlativas(engine: Engine) -> None:
    with engine.begin() as conn:
        assert [siguiente_valor(conn, "inventario:CEN") for _ in range(3)] == [1, 2, 3]
        assert siguiente_valor(conn, "inventario:NOR") == 1


def test_una_transaccion_revertida_no_consume_numeros(engine: Engine) -> None:
    with engine.connect() as conn:
        siguiente_valor(conn, "socio")
        conn.rollback()
    with engine.begin() as conn:
        assert siguiente_valor(conn, "socio") == 1


def test_formatos_de_codigos() -> None:
    assert formatear_codigo_inventario("CEN", 42) == "CEN-000042"
    assert formatear_numero_remito(2026, 7) == "R-2026-000007"


def test_isbn13_con_verificador() -> None:
    # ISBN real de referencia: 978-0-306-40615-7.
    assert isbn13_con_verificador("978030640615") == "9780306406157"


def test_los_datos_iniciales_son_idempotentes(engine: Engine) -> None:
    with engine.begin() as conn:
        cargar_datos_iniciales(conn)
        cargar_datos_iniciales(conn)

    assert _contar(engine, t.parametro) == len(PARAMETROS_INICIALES)
    assert _contar(engine, t.categoria) == len(CATEGORIAS_INICIALES)


def test_los_datos_iniciales_no_pisan_cambios_del_admin(engine: Engine) -> None:
    with engine.begin() as conn:
        cargar_datos_iniciales(conn)
        conn.execute(
            update(t.parametro)
            .where(t.parametro.c.clave == "plazo_prestamo_dias")
            .values(valor="21")
        )
        cargar_datos_iniciales(conn)
        valor = conn.execute(
            select(t.parametro.c.valor).where(t.parametro.c.clave == "plazo_prestamo_dias")
        ).scalar_one()

    assert valor == "21"


def test_la_demo_se_carga_una_sola_vez(engine: Engine) -> None:
    with engine.begin() as conn:
        cargar_datos_iniciales(conn)
        assert cargar_demo(conn) is True
        assert cargar_demo(conn) is False

    assert _contar(engine, t.sede) == 3
    with engine.connect() as conn:
        codigos = conn.execute(select(t.ejemplar.c.codigo_inventario)).scalars().all()
        solo_consulta = conn.execute(
            select(func.count()).select_from(t.ejemplar).where(t.ejemplar.c.prestable.is_(False))
        ).scalar_one()
    assert len(codigos) == len(set(codigos)) > 0
    assert solo_consulta == 1
