"""Concurrencia real sobre PostgreSQL: bloqueos de fila y versión optimista.

Estas pruebas confirman transacciones (no se pueden revertir al final), así que limpian las
tablas de sedes y usuarios antes y después de cada una.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.db.models import LocalidadORM
from app.exceptions import ConflictoDeVersion, SedeEnBaja
from app.models.sede import EstadoSede, UsuarioRef
from app.repositories.impl.sede_repository import SqlAlchemySedeRepository
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.sede_service import SedeService
from tests.factories.datos_orm import crear_admin
from tests.factories.dominio import UsuarioFactory
from tests.factories.sede import datos_sede
from tests.fakes.reloj import RelojFijo
from tests.fakes.verificadores import verificador_con

pytestmark = [pytest.mark.integration, pytest.mark.concurrencia]

TABLAS = "historial_sede, excepcion_horario_sede, horario_sede, socio, sede, usuario"


def _limpiar(engine: Engine) -> None:
    with engine.begin() as con:
        con.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))


@pytest.fixture
def mundo(engine_prueba: Engine) -> Iterator[dict]:
    """Un administrador y una sede ya confirmados en la base."""
    _limpiar(engine_prueba)
    with Session(engine_prueba) as sesion:
        admin_orm = crear_admin(sesion, nombre="Ana Admin")
        localidad = sesion.scalar(select(LocalidadORM.id).where(LocalidadORM.nombre == "Córdoba"))
        admin = UsuarioFactory(id=admin_orm.id, nombre=admin_orm.nombre)
        servicio = SedeService(SqlAlchemyUnitOfWork(sesion), RelojFijo(), verificador_con())
        sede = servicio.crear(admin, "CEN", datos_sede(localidad_id=localidad)).sede
    yield {"admin": admin, "sede_id": sede.id, "localidad": localidad, "engine": engine_prueba}
    _limpiar(engine_prueba)


@contextmanager
def _sesion(engine: Engine) -> Iterator[Session]:
    with Session(engine) as sesion:
        sesion.execute(text("SET lock_timeout = '10s'"))
        yield sesion


def _en_hilo(accion: Callable[[], object]) -> tuple[threading.Thread, dict]:
    resultado: dict = {}

    def correr() -> None:
        try:
            resultado["valor"] = accion()
        except BaseException as error:  # se informa al hilo principal
            resultado["error"] = error

    hilo = threading.Thread(target=correr)
    hilo.start()
    return hilo, resultado


@pytest.mark.ca("CA-SED-41")
def test_dos_modificaciones_con_la_misma_version_solo_una_se_aplica(mundo):
    barrera = threading.Barrier(2)

    def modificar(nombre: str):
        def accion():
            with _sesion(mundo["engine"]) as sesion:
                servicio = SedeService(SqlAlchemyUnitOfWork(sesion), RelojFijo(), verificador_con())
                datos = datos_sede(localidad_id=mundo["localidad"], nombre=nombre)
                barrera.wait(timeout=5)
                return servicio.modificar(mundo["admin"], mundo["sede_id"], 1, datos)

        return _en_hilo(accion)

    (h1, r1), (h2, r2) = modificar("Cambio de A"), modificar("Cambio de B")
    h1.join(15)
    h2.join(15)

    resultados = [r1, r2]
    exitos = [r for r in resultados if "valor" in r]
    fallos = [r["error"] for r in resultados if "error" in r]
    assert len(exitos) == 1 and len(fallos) == 1
    assert isinstance(fallos[0], ConflictoDeVersion)
    assert fallos[0].detalles[0]["version_actual"] == 2
    with _sesion(mundo["engine"]) as sesion:
        sede = SqlAlchemySedeRepository(sesion).obtener(mundo["sede_id"])
        assert sede.version == 2 and sede.nombre == exitos[0]["valor"].sede.nombre


@pytest.mark.ca("CA-SED-42")
def test_la_baja_espera_a_quien_esta_operando_con_la_sede(mundo):
    """Mientras otra transacción opera con la sede (FOR SHARE), la baja no puede tomarla."""
    with _sesion(mundo["engine"]) as operador:
        SqlAlchemySedeRepository(operador).obtener_para_operar(mundo["sede_id"])

        def baja():
            with _sesion(mundo["engine"]) as sesion:
                servicio = SedeService(SqlAlchemyUnitOfWork(sesion), RelojFijo(), verificador_con())
                return servicio.dar_de_baja(mundo["admin"], mundo["sede_id"], 1, "Cierre por obras")

        hilo, resultado = _en_hilo(baja)
        hilo.join(1.0)
        assert hilo.is_alive(), "La baja debería esperar a que termine la operación en curso"
        operador.commit()

    hilo.join(15)
    assert "error" not in resultado, resultado.get("error")
    with _sesion(mundo["engine"]) as sesion:
        assert SqlAlchemySedeRepository(sesion).obtener(mundo["sede_id"]).estado == EstadoSede.BAJA


@pytest.mark.ca("CA-SED-42")
def test_operar_con_una_sede_que_se_esta_dando_de_baja_espera_y_luego_se_rechaza(mundo):
    reloj = RelojFijo()
    with _sesion(mundo["engine"]) as bajista:
        repo = SqlAlchemySedeRepository(bajista)
        sede = repo.obtener_para_modificar(mundo["sede_id"])  # FOR UPDATE: baja en curso

        def operar():
            with _sesion(mundo["engine"]) as sesion:
                return SqlAlchemySedeRepository(sesion).obtener_para_operar(mundo["sede_id"])

        hilo, resultado = _en_hilo(operar)
        hilo.join(1.0)
        assert hilo.is_alive(), "Operar debería esperar a que termine la baja"
        admin = mundo["admin"]
        sede.dar_de_baja(
            motivo="Cierre por obras",
            actor=UsuarioRef(admin.id, admin.nombre),
            ahora=reloj.ahora(),
            impedimentos=[],
        )
        repo.guardar(sede)
        bajista.commit()

    hilo.join(15)
    assert isinstance(resultado.get("error"), SedeEnBaja), resultado
