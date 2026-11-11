"""La base rechaza los estados inválidos aunque el código fallara (restricciones del modelo)."""

from collections.abc import Callable
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import seed
from app.db.models import (
    ExcepcionHorarioSedeORM,
    HistorialSedeORM,
    LocalidadORM,
    ProvinciaORM,
    UsuarioORM,
)
from tests.integration.datos import crear_admin, crear_sede, franja


def debe_fallar(sesion: Session, accion: Callable[[], object]) -> None:
    """La acción debe ser rechazada por la base (en un savepoint, para no invalidar la prueba)."""
    with pytest.raises(DBAPIError), sesion.begin_nested():
        accion()
        sesion.flush()


def test_el_catalogo_contiene_la_provincia_de_cordoba_y_su_capital(sesion: Session):
    provincia = sesion.scalar(select(ProvinciaORM).where(ProvinciaORM.nombre == "Córdoba"))
    capital = sesion.scalar(select(LocalidadORM).where(LocalidadORM.nombre == "Córdoba"))

    assert provincia is not None
    assert capital is not None and capital.departamento == "Capital"
    assert capital.provincia_id == provincia.id


@pytest.mark.parametrize("codigo", ["AB", "abc", "A" * 16, "CEN-1", "CEN 1"])
def test_el_codigo_de_sede_debe_cumplir_el_formato(sesion: Session, codigo: str):
    admin = crear_admin(sesion)

    debe_fallar(sesion, lambda: crear_sede(sesion, admin, codigo=codigo))


def test_el_codigo_de_sede_es_unico(sesion: Session):
    admin = crear_admin(sesion)
    crear_sede(sesion, admin, codigo="CEN_X")

    debe_fallar(sesion, lambda: crear_sede(sesion, admin, codigo="CEN_X"))


def test_el_nombre_normalizado_de_sede_es_unico(sesion: Session):
    admin = crear_admin(sesion)
    crear_sede(sesion, admin, nombre_normalizado="centro")

    debe_fallar(sesion, lambda: crear_sede(sesion, admin, nombre_normalizado="centro"))


def test_una_direccion_repetida_es_valida_porque_se_puede_confirmar(sesion: Session):
    admin = crear_admin(sesion)
    crear_sede(sesion, admin, direccion_normalizada="1|avenida colon|10")

    crear_sede(sesion, admin, direccion_normalizada="1|avenida colon|10")


@pytest.mark.parametrize("telefono", ["3514221234", "+0123456789", "+54351", "+54 351 422 1234"])
def test_el_telefono_debe_estar_en_formato_e164(sesion: Session, telefono: str):
    admin = crear_admin(sesion)

    debe_fallar(sesion, lambda: crear_sede(sesion, admin, telefono=telefono))


def test_los_datos_de_baja_existen_si_y_solo_si_la_sede_esta_en_baja(sesion: Session):
    admin = crear_admin(sesion)

    debe_fallar(sesion, lambda: crear_sede(sesion, admin, estado="BAJA"))
    debe_fallar(
        sesion,
        lambda: crear_sede(
            sesion,
            admin,
            estado="ACTIVA",
            fecha_baja=datetime.now(UTC),
            motivo_baja="x",
            baja_por_id=admin.id,
        ),
    )
    crear_sede(
        sesion,
        admin,
        estado="BAJA",
        fecha_baja=datetime.now(UTC),
        motivo_baja="Obras",
        baja_por_id=admin.id,
    )


@pytest.mark.ca("CA-SED-04", "CA-SED-28")
def test_la_hora_de_cierre_debe_ser_posterior_a_la_apertura(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)

    debe_fallar(sesion, lambda: sesion.add(franja(sede, 1, time(13), time(9))))
    debe_fallar(sesion, lambda: sesion.add(franja(sede, 1, time(9), time(9))))


@pytest.mark.ca("CA-SED-04")
def test_las_franjas_solapadas_del_mismo_dia_son_rechazadas_por_la_base(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    sesion.add(franja(sede, 1, time(9), time(13)))
    sesion.flush()

    debe_fallar(sesion, lambda: sesion.add(franja(sede, 1, time(12), time(16))))


def test_las_franjas_contiguas_o_de_otro_dia_son_validas(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    otra = crear_sede(sesion, admin)

    sesion.add_all(
        [
            franja(sede, 1, time(9), time(13)),
            franja(sede, 1, time(13), time(18)),
            franja(sede, 2, time(9), time(13)),
            franja(otra, 1, time(9), time(13)),
        ]
    )
    sesion.flush()


def _excepcion(sede_id: int, admin_id: int, **over) -> ExcepcionHorarioSedeORM:
    datos = {
        "sede_id": sede_id,
        "fecha": date(2026, 12, 25),
        "tipo": "CIERRE_TOTAL",
        "creado_por_id": admin_id,
    }
    datos.update(over)
    return ExcepcionHorarioSedeORM(**datos)


def test_un_cierre_parcial_exige_horas_y_un_cierre_total_no_las_admite(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)

    debe_fallar(sesion, lambda: sesion.add(_excepcion(sede.id, admin.id, tipo="CIERRE_PARCIAL")))
    debe_fallar(sesion, lambda: sesion.add(_excepcion(sede.id, admin.id, hora_desde=time(9))))
    debe_fallar(
        sesion,
        lambda: sesion.add(
            _excepcion(
                sede.id, admin.id, tipo="CIERRE_PARCIAL", hora_desde=time(18), hora_hasta=time(9)
            )
        ),
    )


@pytest.mark.ca("CA-SED-31")
def test_las_excepciones_de_una_sede_en_la_misma_fecha_no_se_solapan(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    sesion.add(
        _excepcion(
            sede.id, admin.id, tipo="CIERRE_PARCIAL", hora_desde=time(9), hora_hasta=time(12)
        )
    )
    sesion.flush()

    debe_fallar(sesion, lambda: sesion.add(_excepcion(sede.id, admin.id)))  # total
    debe_fallar(
        sesion,
        lambda: sesion.add(
            _excepcion(
                sede.id, admin.id, tipo="CIERRE_PARCIAL", hora_desde=time(11), hora_hasta=time(14)
            )
        ),
    )
    sesion.add(  # contiguo: válido
        _excepcion(
            sede.id, admin.id, tipo="CIERRE_PARCIAL", hora_desde=time(12), hora_hasta=time(14)
        )
    )
    sesion.flush()


def test_un_cierre_total_en_otra_fecha_o_en_otra_sede_es_valido(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    otra = crear_sede(sesion, admin)

    sesion.add_all(
        [
            _excepcion(sede.id, admin.id),
            _excepcion(sede.id, admin.id, fecha=date(2026, 12, 26)),
            _excepcion(otra.id, admin.id),
        ]
    )
    sesion.flush()


def test_el_historial_de_sede_es_de_solo_insercion(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    evento = HistorialSedeORM(
        sede_id=sede.id, tipo_evento="ALTA", usuario_id=admin.id, cambios=[], version_resultante=1
    )
    sesion.add(evento)
    sesion.flush()

    debe_fallar(sesion, lambda: sesion.execute(text("UPDATE historial_sede SET motivo = 'x'")))
    debe_fallar(sesion, lambda: sesion.execute(text("DELETE FROM historial_sede")))


def test_el_historial_solo_admite_tipos_de_evento_conocidos(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)

    debe_fallar(
        sesion,
        lambda: sesion.add(
            HistorialSedeORM(
                sede_id=sede.id,
                tipo_evento="BORRADO",
                usuario_id=admin.id,
                cambios=[],
                version_resultante=1,
            )
        ),
    )


def test_un_bibliotecario_exige_sede_y_un_administrador_no_puede_tenerla(sesion: Session):
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)

    debe_fallar(sesion, lambda: crear_admin(sesion, rol="BIBLIOTECARIO"))
    debe_fallar(sesion, lambda: crear_admin(sesion, rol="ADMIN", sede_id=sede.id))
    crear_admin(sesion, rol="BIBLIOTECARIO", sede_id=sede.id)


def test_el_nombre_de_usuario_debe_estar_en_minusculas_y_ser_unico(sesion: Session):
    crear_admin(sesion, username="ana.lopez")

    debe_fallar(sesion, lambda: crear_admin(sesion, username="Ana.Lopez"))
    debe_fallar(sesion, lambda: crear_admin(sesion, username="ana.lopez"))
    debe_fallar(sesion, lambda: crear_admin(sesion, username="ab"))


def test_un_usuario_socio_exige_la_ficha_de_socio(sesion: Session):
    debe_fallar(sesion, lambda: crear_admin(sesion, rol="SOCIO"))


def test_el_seed_es_idempotente_y_carga_los_datos_de_demostracion(sesion: Session):
    seed.cargar(sesion, "clave-de-demo")
    seed.cargar(sesion, "clave-de-demo")

    usuarios = set(sesion.scalars(select(UsuarioORM.username)))
    assert {"admin", "bibliotecario.cen", "bibliotecario.norte", "socio.demo"} <= usuarios
    codigos = set(sesion.scalars(text("SELECT codigo FROM sede")))
    assert {"CEN", "NORTE", "SUR_RC", "OESTE_VCP"} <= codigos


def test_el_seed_se_niega_fuera_de_desarrollo_y_test(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "entorno", "produccion")

    assert seed.main() == 1
