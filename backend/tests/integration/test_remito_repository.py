"""Remitos e incidencias contra PostgreSQL: restricciones del modelo y solo inserción."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models.usuario import UsuarioRef
from tests.factories.datos_orm import crear_admin, crear_sede
from tests.integration.test_catalogo_repository import _ejemplar, _libro

pytestmark = pytest.mark.integration


@pytest.fixture
def datos(sesion: Session):
    admin = crear_admin(sesion)
    actor = UsuarioRef(admin.id, admin.nombre)
    a, b = crear_sede(sesion, admin), crear_sede(sesion, admin)
    ejemplar = _ejemplar(sesion, actor, _libro(sesion, actor), a.id, "CEN-1")
    return {"a": a, "b": b, "ejemplar": ejemplar}


def _remito(sesion: Session, d, estado: str, despacho: bool, recepcion: bool) -> int:
    return sesion.scalar(
        text(
            "INSERT INTO remito (numero, sede_origen_id, sede_destino_id, motivo, estado, "
            "fecha_generacion, fecha_despacho, fecha_recepcion, version) VALUES "
            "(:n, :a, :b, 'TRASLADO', :e, now(), CASE WHEN :d THEN now() END, "
            "CASE WHEN :r THEN now() END, 1) RETURNING id"
        ),
        {
            "n": f"R-{estado}",
            "a": d["a"].id,
            "b": d["b"].id,
            "e": estado,
            "d": despacho,
            "r": recepcion,
        },
    )


@pytest.mark.ca("CA-REM-26")
@pytest.mark.parametrize(
    ("estado", "despacho", "recepcion", "restriccion"),
    [
        ("DESPACHADO", False, False, "ck_remito_despacho_segun_estado"),
        ("GENERADO", True, False, "ck_remito_despacho_segun_estado"),
        ("RECIBIDO", True, False, "ck_remito_recepcion_segun_estado"),
        ("EN_TRANSITO", True, True, "ck_remito_recepcion_segun_estado"),
    ],
)
def test_las_fechas_del_remito_son_coherentes_con_su_estado(
    sesion: Session, datos, estado, despacho, recepcion, restriccion
):
    with pytest.raises(IntegrityError, match=restriccion):
        _remito(sesion, datos, estado, despacho, recepcion)


def test_un_remito_incompleto_recibido_es_valido(sesion: Session, datos):
    assert _remito(sesion, datos, "INCOMPLETO", despacho=True, recepcion=True)


@pytest.mark.ca("CA-REM-26")
@pytest.mark.parametrize(
    ("llegada", "resultado", "restriccion"),
    [
        ("ROTO", "RECIBIDO", "ck_detalle_remito_estado_fisico_llegada_valido"),
        ("BUENO", "PERDIDO", "ck_detalle_remito_resultado_valido"),
        ("BUENO", "FALTANTE", "ck_detalle_remito_llegada_segun_resultado"),
        (None, "RECIBIDO", "ck_detalle_remito_llegada_segun_resultado"),
    ],
)
def test_el_detalle_del_remito_tiene_valores_coherentes(
    sesion: Session, datos, llegada, resultado, restriccion
):
    remito_id = _remito(sesion, datos, "RECIBIDO", despacho=True, recepcion=True)

    with pytest.raises(IntegrityError, match=restriccion):
        sesion.execute(
            text(
                "INSERT INTO detalle_remito (remito_id, ejemplar_id, estado_fisico_salida, "
                "estado_fisico_llegada, resultado) VALUES (:r, :e, 'BUENO', :l, :res)"
            ),
            {"r": remito_id, "e": datos["ejemplar"].id, "l": llegada, "res": resultado},
        )


@pytest.mark.ca("CA-REM-22")
@pytest.mark.parametrize(
    ("socio", "sede", "restriccion"),
    [
        (True, True, "ck_incidencia_responsable_segun_origen"),  # remito con socio
        (False, False, "ck_incidencia_responsable_segun_origen"),  # remito sin sede responsable
    ],
)
def test_la_incidencia_de_un_remito_tiene_sede_responsable_y_no_socio(
    sesion: Session, datos, socio, sede, restriccion
):
    from app.db.models import SocioORM

    remito_id = _remito(sesion, datos, "DANADO", despacho=True, recepcion=True)
    s = SocioORM(
        numero_socio="00099",
        tipo_documento="DNI",
        nro_documento="30999000",
        nombre="Ana",
        apellido="Lectora",
        sede_alta_id=datos["a"].id,
    )
    sesion.add(s)
    sesion.flush()

    with pytest.raises(IntegrityError, match=restriccion):
        sesion.execute(
            text(
                "INSERT INTO incidencia (tipo, origen, ejemplar_id, remito_id, socio_id, "
                "sede_responsable_id, descripcion, fecha) VALUES ('DANIO', 'REMITO', :e, :r, "
                ":s, :sede, 'Mojado', now())"
            ),
            {
                "e": datos["ejemplar"].id,
                "r": remito_id,
                "s": s.id if socio else None,
                "sede": datos["a"].id if sede else None,
            },
        )


def test_el_historial_del_remito_es_de_solo_insercion(sesion: Session, datos):
    remito_id = _remito(sesion, datos, "GENERADO", despacho=False, recepcion=False)
    sesion.execute(
        text(
            "INSERT INTO movimiento_remito (remito_id, estado_nuevo, observacion) "
            "VALUES (:r, 'GENERADO', 'Remito generado')"
        ),
        {"r": remito_id},
    )

    with pytest.raises(DBAPIError, match="solo inserción"):
        sesion.execute(text("DELETE FROM movimiento_remito WHERE remito_id = :r"), {"r": remito_id})
