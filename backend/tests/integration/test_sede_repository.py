"""Repositorio y servicio de sedes contra PostgreSQL real (esquema creado con Alembic)."""

from datetime import date, time

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import HistorialSedeORM, LocalidadORM
from app.exceptions import SedeCodigoDuplicado, SedeEnBaja, SedeNombreDuplicado
from app.models.horario import TipoExcepcion
from app.models.sede import EstadoSede, TipoEventoSede
from app.models.valores import FranjaHoraria
from app.repositories.impl.sede_repository import (
    SqlAlchemyLocalidadRepository,
    SqlAlchemySedeRepository,
)
from app.repositories.interfaces.sede_repository import (
    FiltroEstado,
    FiltroHistorial,
    FiltroSedes,
    OrdenSedes,
)
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.sede_service import DatosExcepcion, SedeService
from tests.factories.datos_orm import crear_admin
from tests.factories.dominio import UsuarioFactory
from tests.factories.sede import datos_sede
from tests.fakes.verificadores import verificador_con

pytestmark = pytest.mark.integration


@pytest.fixture
def admin(sesion: Session):
    orm = crear_admin(sesion, nombre="Ana Admin")
    return UsuarioFactory(id=orm.id, nombre=orm.nombre)


@pytest.fixture
def localidades(sesion: Session) -> dict[str, int]:
    filas = sesion.scalars(
        select(LocalidadORM).where(LocalidadORM.nombre.in_(["Córdoba", "Río Cuarto"]))
    )
    return {fila.nombre: fila.id for fila in filas}


@pytest.fixture
def servicio(sesion: Session, reloj) -> SedeService:
    return SedeService(SqlAlchemyUnitOfWork(sesion), reloj, verificador_con())


@pytest.fixture
def repo(sesion: Session) -> SqlAlchemySedeRepository:
    return SqlAlchemySedeRepository(sesion)


def _alta(servicio, admin, localidades, codigo="CEN", **over):
    datos = datos_sede(localidad_id=localidades["Córdoba"], **over)
    return servicio.crear(admin, codigo, datos).sede


def test_el_alta_se_persiste_con_horarios_nombres_y_evento(
    servicio, admin, repo, localidades, sesion
):
    sede = _alta(servicio, admin, localidades, nombre="Sede Central")

    leida = repo.obtener(sede.id)
    assert leida is not None and leida.codigo.valor == "CEN" and leida.version == 1
    assert leida.creado_por.nombre == "Ana Admin" and leida.actualizado_por.id == admin.id
    assert leida.direccion.localidad.nombre == "Córdoba"
    assert leida.direccion.localidad.provincia == "Córdoba"
    assert [(f.dia, f.apertura) for f in leida.horarios][0] == (1, time(9, 0))
    eventos = sesion.scalars(
        select(HistorialSedeORM).where(HistorialSedeORM.sede_id == sede.id)
    ).all()
    assert [e.tipo_evento for e in eventos] == ["ALTA"]


def test_codigo_y_nombre_duplicados_los_rechaza_la_base(servicio, admin, repo, localidades, sesion):
    _alta(servicio, admin, localidades, "CEN", nombre="Centro")
    cantidad = len(repo.listar(FiltroSedes(), 1, 50)[0])

    # La base es la última defensa: se salta la verificación previa del servicio.
    de_nuevo = datos_sede(localidad_id=localidades["Córdoba"], nombre="Otro nombre")
    sede = servicio.crear(admin, "OTRO", de_nuevo).sede
    sede.codigo = type(sede.codigo)("CEN")
    sede.id = None
    with pytest.raises(SedeCodigoDuplicado):
        repo.agregar(sede)

    sede.codigo = type(sede.codigo)("NUEVO")
    sede.nombre = "CENTRO"
    sede.id = None
    with pytest.raises(SedeNombreDuplicado):
        repo.agregar(sede)
    assert len(repo.listar(FiltroSedes(), 1, 50)[0]) == cantidad + 1  # solo la de "OTRO"


def test_modificar_reemplaza_los_horarios_sin_chocar_con_la_restriccion(
    servicio, admin, repo, localidades
):
    sede = _alta(servicio, admin, localidades)
    nuevos = [FranjaHoraria(1, time(9), time(12)), FranjaHoraria(1, time(12), time(15))]

    servicio.modificar(
        admin,
        sede.id,
        1,
        datos_sede(localidad_id=localidades["Córdoba"], nombre=sede.nombre, horarios=nuevos),
    )

    leida = repo.obtener(sede.id)
    assert [(f.dia, f.apertura, f.cierre) for f in leida.horarios] == [
        (1, time(9), time(12)),
        (1, time(12), time(15)),
    ]
    assert leida.version == 2


def test_baja_y_reactivacion_persisten_y_limpian_los_datos_de_baja(
    servicio, admin, repo, localidades, sesion
):
    sede = _alta(servicio, admin, localidades)

    servicio.dar_de_baja(admin, sede.id, 1, "Cierre por obras")
    en_baja = repo.obtener(sede.id)
    assert en_baja.estado == EstadoSede.BAJA and en_baja.baja.motivo == "Cierre por obras"
    assert en_baja.baja.usuario.nombre == "Ana Admin"
    with pytest.raises(SedeEnBaja):
        repo.obtener_para_operar(sede.id)

    servicio.reactivar(admin, sede.id, 2)
    activa = repo.obtener_para_operar(sede.id)
    assert activa.baja is None and activa.version == 3
    historial, total = repo.historial(sede.id, FiltroHistorial(), 1, 20)
    assert total == 3
    assert [e.tipo for e in historial] == [
        TipoEventoSede.REACTIVACION,
        TipoEventoSede.BAJA,
        TipoEventoSede.ALTA,
    ]


def test_las_excepciones_reciben_id_y_se_eliminan(servicio, admin, repo, localidades):
    sede = _alta(servicio, admin, localidades)

    creadas = servicio.agregar_excepciones(
        admin,
        sede.id,
        DatosExcepcion(
            date(2026, 12, 1), date(2026, 12, 3), TipoExcepcion.CIERRE_TOTAL, motivo="Obras"
        ),
    )
    assert all(e.id for e in creadas) and len({e.id for e in creadas}) == 3
    assert [e.fecha.day for e in repo.obtener(sede.id).excepciones] == [1, 2, 3]

    servicio.quitar_excepcion(admin, sede.id, creadas[1].id)
    assert [e.fecha.day for e in repo.obtener(sede.id).excepciones] == [1, 3]
    assert repo.obtener(sede.id).version == 1


def test_el_listado_filtra_ordena_y_busca_sin_distinguir_tildes(servicio, admin, repo, localidades):
    _alta(servicio, admin, localidades, "CEN", nombre="Sede Centro")
    rc = servicio.crear(
        admin,
        "RIO_C",
        datos_sede(localidad_id=localidades["Río Cuarto"], nombre="Sede Sur"),
    ).sede
    baja = _alta(servicio, admin, localidades, "OESTE", nombre="Sede Oeste")
    servicio.dar_de_baja(admin, baja.id, 1, "Cierre temporal")

    todas, total = repo.listar(FiltroSedes(orden=OrdenSedes.NOMBRE_DESC), 1, 10)
    assert total == 3 and [s.nombre for s in todas] == ["Sede Sur", "Sede Oeste", "Sede Centro"]
    activas, total = repo.listar(FiltroSedes(estado=FiltroEstado.ACTIVA), 1, 10)
    assert total == 2 and {s.codigo.valor for s in activas} == {"CEN", "RIO_C"}
    assert repo.listar(FiltroSedes(texto="rio cuarto"), 1, 10)[0][0].id == rc.id  # por localidad
    assert [s.codigo.valor for s in repo.listar(FiltroSedes(texto="cen"), 1, 10)[0]] == ["CEN"]
    assert repo.listar(FiltroSedes(texto="100%"), 1, 10)[1] == 0  # sin comodines
    pagina2, total = repo.listar(FiltroSedes(orden=OrdenSedes.CODIGO), 2, 2)
    assert total == 3 and len(pagina2) == 1
    assert repo.contar_por_estado() == {"ACTIVA": 2, "BAJA": 1}


def test_busqueda_por_direccion_y_nombre_normalizado(servicio, admin, repo, localidades):
    sede = _alta(servicio, admin, localidades, nombre="Sede Ñandú", calle="Av. Colón", numero="250")

    assert [s.id for s in repo.buscar_por_direccion(sede.direccion.normalizada())] == [sede.id]
    assert repo.buscar_por_direccion(sede.direccion.normalizada(), excluir_id=sede.id) == []
    assert repo.buscar_por_nombre_normalizado("sede nandu").id == sede.id
    assert repo.buscar_por_nombre_normalizado("sede nandu", excluir_id=sede.id) is None
    assert repo.buscar_por_codigo("CEN").id == sede.id
    assert repo.buscar_por_codigo("NOPE") is None


def test_el_historial_pagina_y_filtra_por_tipo(servicio, admin, repo, localidades):
    sede = _alta(servicio, admin, localidades)
    servicio.modificar(
        admin, sede.id, 1, datos_sede(localidad_id=localidades["Córdoba"], nombre="Nuevo nombre")
    )
    servicio.dar_de_baja(admin, sede.id, 2, "Cierre temporal")

    pagina, total = repo.historial(sede.id, FiltroHistorial(), 1, 2)
    assert total == 3 and len(pagina) == 2
    solo, total = repo.historial(
        sede.id, FiltroHistorial(tipo_evento=TipoEventoSede.MODIFICACION), 1, 10
    )
    assert total == 1
    cambio = {c.campo: (c.antes, c.despues) for c in solo[0].cambios}
    assert cambio["nombre"][1] == "Nuevo nombre"


def test_el_catalogo_de_localidades(sesion, localidades):
    repo = SqlAlchemyLocalidadRepository(sesion)

    assert repo.obtener(localidades["Córdoba"]).provincia == "Córdoba"
    assert repo.obtener(999_999) is None
    assert [loc.nombre for loc in repo.listar(texto="rio cuarto")] == ["Río Cuarto"]
    assert repo.listar(provincia_id=999_999) == []
    assert [nombre for _, nombre in repo.provincias()] == ["Córdoba"]
