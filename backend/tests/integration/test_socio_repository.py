"""Repositorio de socios contra PostgreSQL real (esquema creado con Alembic)."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
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
    TipoBaja,
    TipoDocumento,
    TipoEventoSocio,
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


def _rechaza(sesion: Session, cambiar) -> None:
    with pytest.raises(DBAPIError), sesion.begin_nested():
        cambiar()
        sesion.flush()


def test_la_baja_la_solicitud_y_el_historial_se_guardan_y_se_recuperan(sesion: Session):
    repo = SqlAlchemySocioRepository(sesion)
    socio = _socio_guardado(sesion, repo)
    actor = socio.creado_por
    socio.inhabilitar("Daño reiterado de material", actor=actor, ahora=AHORA)
    socio.dar_de_baja(
        SituacionSocio(),
        TipoBaja.A_PEDIDO,
        "Se mudó",
        actor=actor,
        es_administrador=True,
        ahora=AHORA,
    )
    socio.solicitar_reactivacion("Volví", actor=actor, ahora=AHORA)
    repo.guardar(socio)
    sesion.expire_all()

    recargado = repo.obtener(socio.id)
    eventos, total = repo.historial(socio.id, 1, 10)

    assert (recargado.estado, recargado.tipo_baja) == (EstadoSocio.BAJA, TipoBaja.A_PEDIDO)
    assert recargado.causas == {MotivoInhabilitacion.ADMINISTRATIVA}  # sobrevive a la baja
    assert recargado.solicitud.mensaje == "Volví"
    assert total == 4 and [e.tipo for e in eventos] == [
        TipoEventoSocio.SOLICITUD_REACTIVACION,
        TipoEventoSocio.BAJA,
        TipoEventoSocio.INHABILITACION,
        TipoEventoSocio.ALTA,
    ]
    assert eventos[1].cambios[0].despues == "A_PEDIDO" and eventos[0].usuario.id == actor.id


def test_el_historial_del_socio_es_de_solo_insercion(sesion: Session):
    repo = SqlAlchemySocioRepository(sesion)
    socio = _socio_guardado(sesion, repo)

    for sentencia in ("UPDATE historial_socio SET motivo = 'x'", "DELETE FROM historial_socio"):
        with pytest.raises(DBAPIError, match="solo inserción"), sesion.begin_nested():
            sesion.execute(text(f"{sentencia} WHERE socio_id = :id"), {"id": socio.id})


def test_la_base_controla_baja_causas_y_solicitud(sesion: Session):
    repo = SqlAlchemySocioRepository(sesion)
    socio = _socio_guardado(sesion, repo)
    fila = sesion.get(SocioORM, socio.id)

    def baja_sin_tipo() -> None:
        fila.estado, fila.fecha_baja, fila.motivo_baja = "BAJA", AHORA, "Se mudó"

    def baja_con_causa_automatica() -> None:
        baja_sin_tipo()
        fila.tipo_baja, fila.causa_multa_impaga = "A_PEDIDO", True
        fila.motivo_inhabilitacion = "MULTA_IMPAGA"

    def solicitud_sin_baja() -> None:
        fila.reactivacion_solicitada_en = AHORA

    for cambio in (baja_sin_tipo, baja_con_causa_automatica, solicitud_sin_baja):
        _rechaza(sesion, cambio)
        sesion.refresh(fila)
