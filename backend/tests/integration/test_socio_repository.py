"""Repositorio de socios contra PostgreSQL real (esquema creado con Alembic)."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import SocioORM
from app.models.socio import (
    DatosPersonales,
    Documento,
    EstadoSocio,
    MotivoInhabilitacion,
    SituacionSocio,
    Socio,
    TipoDocumento,
)
from app.models.usuario import UsuarioRef
from app.repositories.impl.socio_repository import SqlAlchemySocioRepository
from tests.factories.datos_orm import crear_admin, crear_sede

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


def _socio_guardado(sesion: Session, repo: SqlAlchemySocioRepository) -> Socio:
    admin = crear_admin(sesion)
    sede = crear_sede(sesion, admin)
    datos = DatosPersonales.crear(
        documento=Documento.crear(TipoDocumento.DNI, "30111222"),
        nombre="Lucía",
        apellido="Gómez",
        fecha_nacimiento=None,
        email="lucia@example.com",
        telefono=None,
        domicilio=None,
        hoy=date(2026, 11, 10),
    )
    socio = Socio.registrar(
        numero_socio=repo.siguiente_numero(),
        datos=datos,
        sede_alta_id=sede.id,
        actor=UsuarioRef(admin.id, admin.nombre),
        ahora=AHORA,
    )
    repo.agregar(socio)
    return socio


def test_las_causas_automaticas_se_guardan_y_se_recuperan_completas(sesion: Session):
    repo = SqlAlchemySocioRepository(sesion)
    socio = _socio_guardado(sesion, repo)
    situacion = SituacionSocio(prestamos_vencidos=1, multas_pendientes=1)
    socio.reevaluar(situacion, actor=None, ahora=AHORA)
    repo.guardar(socio)
    sesion.expire_all()

    recargado = repo.obtener(socio.id)

    assert recargado.estado == EstadoSocio.INHABILITADO
    assert recargado.causas == {
        MotivoInhabilitacion.PRESTAMO_VENCIDO,
        MotivoInhabilitacion.MULTA_IMPAGA,
    }
    assert recargado.motivo_inhabilitacion == MotivoInhabilitacion.PRESTAMO_VENCIDO
    # Sin cambios reales, reevaluar no vuelve a escribir el socio.
    assert recargado.reevaluar(situacion, actor=None, ahora=AHORA) is False


def test_la_base_rechaza_un_inhabilitado_sin_causas(sesion: Session):
    repo = SqlAlchemySocioRepository(sesion)
    socio = _socio_guardado(sesion, repo)
    fila = sesion.get(SocioORM, socio.id)

    with pytest.raises(DBAPIError), sesion.begin_nested():
        fila.estado = "INHABILITADO"
        fila.motivo_inhabilitacion = "MULTA_IMPAGA"
        sesion.flush()
