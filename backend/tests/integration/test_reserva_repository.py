"""Reservas contra PostgreSQL: cola FIFO, historial de solo inserción y datos según el estado."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.db.models import SocioORM
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum as R
from app.models.usuario import UsuarioRef
from app.repositories.impl.reserva_repository import SqlAlchemyReservaRepository
from app.repositories.interfaces.prestamo_repository import FiltroReservas
from tests.factories.datos_orm import crear_admin, crear_sede
from tests.integration.test_catalogo_repository import _ejemplar, _libro

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


@pytest.fixture
def datos(sesion: Session):
    admin = crear_admin(sesion)
    actor = UsuarioRef(admin.id, admin.nombre)
    sede = crear_sede(sesion, admin)
    libro = _libro(sesion, actor)
    socios = []
    for i in range(3):
        socio = SocioORM(
            numero_socio=f"0008{i}",
            tipo_documento="DNI",
            nro_documento=f"3088800{i}",
            nombre=f"Socio{i}",
            apellido="Lector",
            sede_alta_id=sede.id,
        )
        sesion.add(socio)
        socios.append(socio)
    sesion.flush()
    ejemplar = _ejemplar(sesion, actor, libro, sede.id, "CEN-1")
    return {"actor": actor, "sede": sede, "libro": libro, "socios": socios, "ejemplar": ejemplar}


def _nueva(repo: SqlAlchemyReservaRepository, d, socio: int, ahora: datetime) -> Reserva:
    reserva = Reserva.registrar(
        numero=repo.siguiente_numero(2026),
        socio_id=d["socios"][socio].id,
        libro_id=d["libro"].id,
        sede_retiro_id=d["sede"].id,
        actor=d["actor"],
        ahora=ahora,
    )
    repo.agregar(reserva)
    return reserva


@pytest.mark.ca("CA-RES-22")
def test_la_cola_respeta_el_orden_de_llegada_y_desempata_por_id(sesion: Session, datos):
    repo = SqlAlchemyReservaRepository(sesion)
    tercera = _nueva(repo, datos, 0, AHORA + timedelta(minutes=5))
    primera = _nueva(repo, datos, 1, AHORA)
    segunda = _nueva(repo, datos, 2, AHORA)  # misma hora que la primera, id mayor

    cola = repo.cola_del_libro(datos["libro"].id)
    listado, total = repo.listar(FiltroReservas(libro_id=datos["libro"].id, orden_cola=True), 1, 10)

    esperado = [primera.id, segunda.id, tercera.id]
    assert [r.id for r in cola] == esperado
    assert [r.id for r in listado] == esperado and total == 3
    assert [r.posicion_en_cola for r in listado] == [1, 2, 3]


@pytest.mark.ca("CA-RES-19")
def test_el_historial_se_guarda_con_autor_y_es_de_solo_insercion(sesion: Session, datos):
    repo = SqlAlchemyReservaRepository(sesion)
    reserva = _nueva(repo, datos, 0, AHORA)
    reserva.asignar(datos["ejemplar"].id, date(2026, 11, 10), 3, AHORA, "CEN-1")
    repo.guardar(reserva)
    assert reserva.id is not None

    historial = repo.historial(reserva.id)
    leida = repo.obtener(reserva.id)

    assert [(m.estado_anterior, m.estado_nuevo, m.usuario) for m in historial] == [
        (None, R.PENDIENTE, datos["actor"]),
        (R.PENDIENTE, R.DISPONIBLE_PARA_RETIRO, None),
    ]
    assert leida is not None and leida.registrada_por == datos["actor"]
    with pytest.raises(DBAPIError, match="solo inserción"):
        sesion.execute(text("UPDATE movimiento_reserva SET observacion = 'x'"))


@pytest.mark.ca("CA-RES-19")
@pytest.mark.parametrize(
    ("estado", "columnas"),
    [
        ("PENDIENTE", {"fecha_cierre": "now()"}),
        ("DISPONIBLE_PARA_RETIRO", {}),
        ("CUMPLIDA", {"fecha_cierre": "now()"}),  # sin préstamo
        ("VENCIDA", {}),  # sin ejemplar ni cierre
        ("CANCELADA", {}),  # sin cierre
    ],
)
def test_los_datos_de_la_reserva_son_coherentes_con_su_estado(
    sesion: Session, datos, estado, columnas
):
    extra = "".join(f", {c}" for c in columnas)
    valores = "".join(f", {v}" for v in columnas.values())
    with pytest.raises(IntegrityError, match="ck_reserva_datos_segun_estado"):
        sesion.execute(
            text(
                "INSERT INTO reserva (numero, socio_id, libro_id, sede_retiro_id, estado, "
                f"fecha_reserva{extra}) VALUES ('RS-X', :s, :l, :sede, :e, now(){valores})"
            ),
            {
                "s": datos["socios"][0].id,
                "l": datos["libro"].id,
                "sede": datos["sede"].id,
                "e": estado,
            },
        )
