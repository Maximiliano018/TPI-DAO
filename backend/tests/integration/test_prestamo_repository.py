"""Préstamos contra PostgreSQL: restricciones de fechas y disponibilidad para la autogestión."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import SocioORM
from app.repositories.impl.catalogo_repository import SqlAlchemyEjemplarRepository
from tests.factories.datos_orm import crear_admin, crear_sede
from tests.integration.test_catalogo_repository import _ejemplar, _libro

pytestmark = pytest.mark.integration


@pytest.fixture
def datos(sesion: Session):
    from app.models.usuario import UsuarioRef

    admin = crear_admin(sesion)
    actor = UsuarioRef(admin.id, admin.nombre)
    a, b = crear_sede(sesion, admin), crear_sede(sesion, admin)
    libro = _libro(sesion, actor)
    socio = SocioORM(
        numero_socio="00077",
        tipo_documento="DNI",
        nro_documento="30777888",
        nombre="Ana",
        apellido="Lectora",
        sede_alta_id=a.id,
    )
    sesion.add(socio)
    sesion.flush()
    return {"actor": actor, "a": a, "b": b, "libro": libro, "socio": socio}


def _insertar(sesion: Session, d, ejemplar_id: int, estado: str, **fechas) -> None:
    columnas = {"fecha_inicio": None, "fecha_vencimiento": None, "fecha_devolucion": None}
    columnas.update(fechas)
    sesion.execute(
        text(
            "INSERT INTO prestamo (numero, socio_id, ejemplar_id, tipo, sede_origen_id, "
            "sede_destino_id, estado, fecha_solicitud, renovaciones, fecha_inicio, "
            "fecha_vencimiento, fecha_devolucion) VALUES ('P-X', :s, :e, 'LOCAL', :a, :a, "
            ":estado, now(), 0, :fecha_inicio, :fecha_vencimiento, :fecha_devolucion)"
        ),
        {"s": d["socio"].id, "e": ejemplar_id, "a": d["a"].id, "estado": estado, **columnas},
    )


@pytest.mark.ca("CA-PRE-30")
@pytest.mark.parametrize(
    ("estado", "fechas", "restriccion"),
    [
        ("ACTIVO", {}, "ck_prestamo_fechas_segun_estado"),
        (
            "SOLICITADO",
            {"fecha_inicio": "2026-11-10", "fecha_vencimiento": "2026-11-24"},
            "ck_prestamo_fechas_segun_estado",
        ),
        (
            "DEVUELTO",
            {"fecha_inicio": "2026-11-10", "fecha_vencimiento": "2026-11-24"},
            "ck_prestamo_devolucion_con_fecha",
        ),
    ],
)
def test_las_fechas_del_prestamo_son_coherentes_con_su_estado(
    sesion: Session, datos, estado, fechas, restriccion
):
    ejemplar = _ejemplar(sesion, datos["actor"], datos["libro"], datos["a"].id, "CEN-1")

    with pytest.raises(IntegrityError, match=restriccion):
        _insertar(sesion, datos, ejemplar.id, estado, **fechas)


def test_un_prestamo_devuelto_con_todas_sus_fechas_es_valido(sesion: Session, datos):
    ejemplar = _ejemplar(sesion, datos["actor"], datos["libro"], datos["a"].id, "CEN-1")

    _insertar(
        sesion,
        datos,
        ejemplar.id,
        "DEVUELTO",
        fecha_inicio="2026-11-10",
        fecha_vencimiento="2026-11-24",
        fecha_devolucion="2026-11-20T12:00:00Z",
    )


@pytest.mark.ca("CA-PRE-20")
def test_disponibles_por_sede_cuenta_solo_los_que_estan_en_su_sede_activa(sesion: Session, datos):
    repo = SqlAlchemyEjemplarRepository(sesion)
    libro, a, b = datos["libro"], datos["a"], datos["b"]
    _ejemplar(sesion, datos["actor"], libro, a.id, "A-1")
    _ejemplar(sesion, datos["actor"], libro, b.id, "B-1")
    fuera = _ejemplar(sesion, datos["actor"], libro, b.id, "B-2")
    sesion.execute(
        text("UPDATE ejemplar SET sede_actual_id = :a WHERE id = :id"), {"a": a.id, "id": fuera.id}
    )
    assert libro.id is not None

    assert repo.disponibles_por_sede(libro.id) == {a.id: 1, b.id: 1}
    tomado = repo.tomar_disponible(libro.id, b.id)
    assert tomado is not None and tomado.codigo_inventario == "B-1"
