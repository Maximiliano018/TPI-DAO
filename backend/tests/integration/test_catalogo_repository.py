"""Repositorios del catálogo contra PostgreSQL real (esquema creado con Alembic)."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import LibroDuplicado
from app.models.ejemplar import Ejemplar, EstadoFisico, TipoMovimiento
from app.models.libro import CategoriaRef, DatosLibro, Isbn, Libro, TipoMaterial
from app.models.sede import Cambio
from app.models.usuario import UsuarioRef
from app.repositories.impl.catalogo_repository import (
    SqlAlchemyEjemplarRepository,
    SqlAlchemyLibroRepository,
)
from tests.factories.datos_orm import crear_admin, crear_sede

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


def _categoria(sesion: Session) -> CategoriaRef:
    fila = sesion.execute(text("SELECT id, nombre FROM categoria ORDER BY id LIMIT 1")).one()
    return CategoriaRef(fila.id, fila.nombre)


def _datos(sesion: Session, **over) -> DatosLibro:
    valores = {
        "isbn": "9789500705783",
        "titulo": "Rayuela",
        "autores": ["Julio Cortázar"],
        "editorial": "Sudamericana",
        "anio_edicion": 1963,
        "categoria": _categoria(sesion),
        "tipo_material": TipoMaterial.LIBRO,
        "anio_actual": 2026,
    }
    valores.update(over)
    return DatosLibro.crear(**valores)


@pytest.fixture
def actor(sesion: Session) -> UsuarioRef:
    admin = crear_admin(sesion)
    return UsuarioRef(admin.id, admin.nombre)


def _libro(sesion: Session, actor: UsuarioRef, **over) -> Libro:
    libro = Libro.crear(_datos(sesion, **over), actor=actor, ahora=AHORA)
    SqlAlchemyLibroRepository(sesion).agregar(libro)
    return libro


def _ejemplar(sesion: Session, actor: UsuarioRef, libro: Libro, sede_id: int, codigo: str):
    assert libro.id is not None
    ejemplar = Ejemplar.registrar(
        codigo_inventario=codigo,
        libro_id=libro.id,
        sede_id=sede_id,
        estado_fisico=EstadoFisico.BUENO,
        observaciones=None,
        actor=actor,
        ahora=AHORA,
    )
    SqlAlchemyEjemplarRepository(sesion).agregar(ejemplar)
    return ejemplar


# --- libros ----------------------------------------------------------------------------------


def test_el_mismo_autor_con_o_sin_tildes_se_guarda_una_sola_vez(sesion: Session, actor):
    _libro(sesion, actor)
    _libro(sesion, actor, isbn="9789875801233", titulo="Bestiario", autores=["JULIO CORTAZAR"])

    assert sesion.scalar(text("SELECT count(*) FROM autor")) == 1


def test_modificar_guarda_autores_en_orden_y_la_version(sesion: Session, actor):
    repo = SqlAlchemyLibroRepository(sesion)
    libro = _libro(sesion, actor)
    nuevos = _datos(sesion, autores=["Julio Cortázar", "Saúl Yurkievich"])

    assert libro.modificar(nuevos, actor=actor, ahora=AHORA)
    repo.guardar(libro)
    sesion.expire_all()

    assert libro.id is not None
    leido = repo.obtener(libro.id)
    assert leido is not None
    assert (leido.datos.autores, leido.version) == (("Julio Cortázar", "Saúl Yurkievich"), 2)


def test_un_isbn_repetido_al_guardar_se_traduce_a_libro_duplicado(sesion: Session, actor):
    """Aunque cambien los autores (cuyo flush va antes), el choque se informa como 409."""
    repo = SqlAlchemyLibroRepository(sesion)
    _libro(sesion, actor, isbn="9789875801233", titulo="Bestiario")
    libro = _libro(sesion, actor)
    libro.datos = replace(
        libro.datos, isbn=Isbn("9789875801233"), autores=("Otro Autor",), titulo="Rayuela 2"
    )

    with pytest.raises(LibroDuplicado):
        repo.guardar(libro)


def test_los_conteos_separan_registrados_vigentes_y_disponibles(sesion: Session, actor):
    sede = crear_sede(sesion, crear_admin(sesion, username="otro.admin"))
    libro = _libro(sesion, actor)
    _ejemplar(sesion, actor, libro, sede.id, "CEN-1")
    baja = _ejemplar(sesion, actor, libro, sede.id, "CEN-2")
    baja.dar_de_baja("Destruido por agua", actor, AHORA)
    SqlAlchemyEjemplarRepository(sesion).guardar(baja)

    assert libro.id is not None
    leido = SqlAlchemyLibroRepository(sesion).obtener(libro.id)
    assert leido is not None
    assert (leido.ejemplares_registrados, leido.cantidad_ejemplares, leido.disponibles) == (
        2,
        1,
        1,
    )
    assert not leido.eliminable


def test_un_libro_debe_tener_isbn_o_clave_natural(sesion: Session, actor):
    libro = _libro(sesion, actor)

    with pytest.raises(IntegrityError, match="ck_libro_isbn_o_clave"):
        sesion.execute(
            text("UPDATE libro SET clave_natural = 'x' WHERE id = :id"), {"id": libro.id}
        )


# --- ejemplares ------------------------------------------------------------------------------


def test_el_historial_guarda_los_cambios_y_devuelve_las_sedes_por_nombre(sesion: Session, actor):
    admin = crear_admin(sesion, username="otro.admin")
    centro, norte = crear_sede(sesion, admin), crear_sede(sesion, admin)
    repo = SqlAlchemyEjemplarRepository(sesion)
    ejemplar = _ejemplar(sesion, actor, _libro(sesion, actor), centro.id, "CEN-1")

    ejemplar.apartar(actor, AHORA, "Traslado en el remito R-1")
    ejemplar.poner_en_transito(actor, AHORA, "Despachado")
    ejemplar.recibir_en(
        norte.id,
        EstadoFisico.REGULAR,
        trasladar=True,
        actor=actor,
        ahora=AHORA,
        observacion="Recibido en R-1",
    )
    ejemplar.liberar(actor, AHORA, "Recibido en R-1")
    repo.guardar(ejemplar)

    assert ejemplar.id is not None
    historial = repo.historial(ejemplar.id)
    assert [m.tipo for m in historial] == [
        TipoMovimiento.ALTA,
        TipoMovimiento.CAMBIO_DE_ESTADO,
        TipoMovimiento.CAMBIO_DE_ESTADO,
        TipoMovimiento.TRASLADO,
        TipoMovimiento.CAMBIO_DE_ESTADO,
    ]
    assert historial[3].cambios == (
        Cambio("sede_actual", centro.nombre, norte.nombre),
        Cambio("sede_propietaria", centro.nombre, norte.nombre),
        Cambio("estado_fisico", "BUENO", "REGULAR"),
    )
    guardado = sesion.scalar(
        text("SELECT cambios FROM movimiento_ejemplar WHERE ejemplar_id = :id ORDER BY id DESC"),
        {"id": ejemplar.id},
    )
    assert guardado == []  # la liberación no cambió otros datos


def test_un_ejemplar_en_baja_exige_fecha_y_motivo(sesion: Session, actor):
    sede = crear_sede(sesion, crear_admin(sesion, username="otro.admin"))
    ejemplar = _ejemplar(sesion, actor, _libro(sesion, actor), sede.id, "CEN-1")

    with pytest.raises(IntegrityError, match="ck_ejemplar_baja_con_datos"):
        sesion.execute(
            text("UPDATE ejemplar SET estado = 'BAJA' WHERE id = :id"), {"id": ejemplar.id}
        )


@pytest.mark.parametrize("codigo", ["ab", "-ABC", "CEN 001", "cen-001"])
def test_el_codigo_de_inventario_debe_cumplir_el_formato(sesion: Session, actor, codigo):
    sede = crear_sede(sesion, crear_admin(sesion, username="otro.admin"))
    ejemplar = _ejemplar(sesion, actor, _libro(sesion, actor), sede.id, "CEN-1")

    with pytest.raises(IntegrityError, match="ck_ejemplar_codigo_formato"):
        sesion.execute(
            text("UPDATE ejemplar SET codigo_inventario = :c WHERE id = :id"),
            {"c": codigo, "id": ejemplar.id},
        )


def test_el_historial_del_ejemplar_es_de_solo_insercion(sesion: Session, actor):
    sede = crear_sede(sesion, crear_admin(sesion, username="otro.admin"))
    ejemplar = _ejemplar(sesion, actor, _libro(sesion, actor), sede.id, "CEN-1")

    with pytest.raises(DBAPIError, match="solo inserción"):
        sesion.execute(
            text("UPDATE movimiento_ejemplar SET cambios = '[]' WHERE ejemplar_id = :id"),
            {"id": ejemplar.id},
        )
