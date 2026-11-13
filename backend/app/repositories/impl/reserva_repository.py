"""Repositorio de reservas sobre SQLAlchemy."""

from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import LibroORM, ReservaORM
from app.db.models.prestamo import SECUENCIA_RESERVA
from app.exceptions import ReservaDuplicada
from app.models.prestamo import formatear_numero
from app.models.reserva import Reserva
from app.models.states.reserva import ACTIVAS, EstadoReservaEnum, estado_reserva
from app.repositories.interfaces.prestamo_repository import FiltroReservas

_ACTIVAS = [e.value for e in ACTIVAS]
_PENDIENTE = EstadoReservaEnum.PENDIENTE.value


def _a_dominio(orm: ReservaORM, titulos: dict[int, str]) -> Reserva:
    return Reserva(
        id=orm.id,
        numero=orm.numero,
        socio_id=orm.socio_id,
        libro_id=orm.libro_id,
        sede_retiro_id=orm.sede_retiro_id,
        fecha_reserva=orm.fecha_reserva,
        estado=estado_reserva(orm.estado),
        ejemplar_id=orm.ejemplar_id,
        vencimiento_retiro=orm.vencimiento_retiro,
        prestamo_id=orm.prestamo_id,
        fecha_cierre=orm.fecha_cierre,
        socio_nombre=f"{orm.socio.nombre} {orm.socio.apellido}",
        numero_socio=orm.socio.numero_socio,
        libro_titulo=titulos.get(orm.libro_id),
        sede_retiro_nombre=orm.sede_retiro.nombre,
        codigo_ejemplar=orm.ejemplar.codigo_inventario if orm.ejemplar else None,
    )


class SqlAlchemyReservaRepository:
    """Implementa ``ReservaRepository``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def siguiente_numero(self, anio: int) -> str:
        valor = self._sesion.scalar(SECUENCIA_RESERVA.next_value())
        assert valor is not None
        return formatear_numero("RS", anio, int(valor))

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, reserva_id: int) -> Reserva | None:
        return self._uno(select(ReservaORM).where(ReservaORM.id == reserva_id))

    def obtener_para_modificar(self, reserva_id: int) -> Reserva | None:
        return self._uno(
            select(ReservaORM)
            .where(ReservaORM.id == reserva_id)
            .with_for_update(of=ReservaORM)
            .execution_options(populate_existing=True)
        )

    def activas_de_socio(self, socio_id: int) -> list[Reserva]:
        return self._varios(
            select(ReservaORM).where(
                ReservaORM.socio_id == socio_id, ReservaORM.estado.in_(_ACTIVAS)
            )
        )

    def cola_del_libro(self, libro_id: int) -> list[Reserva]:
        return self._varios(
            select(ReservaORM)
            .where(ReservaORM.libro_id == libro_id, ReservaORM.estado == _PENDIENTE)
            .order_by(ReservaORM.fecha_reserva, ReservaORM.id)
            .with_for_update(of=ReservaORM)
        )

    def vencidas(self, hoy: date) -> list[Reserva]:
        return self._varios(
            select(ReservaORM)
            .where(
                ReservaORM.estado == EstadoReservaEnum.DISPONIBLE_PARA_RETIRO.value,
                ReservaORM.vencimiento_retiro < hoy,
            )
            .order_by(ReservaORM.id)
            .with_for_update(of=ReservaORM)
        )

    def hay_pendientes(self, libro_id: int) -> bool:
        cantidad = self._sesion.scalar(
            select(func.count(ReservaORM.id)).where(
                ReservaORM.libro_id == libro_id, ReservaORM.estado == _PENDIENTE
            )
        )
        return bool(cantidad)

    def listar(self, filtro: FiltroReservas, page: int, size: int) -> tuple[list[Reserva], int]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.socio_id is not None:
            condiciones.append(ReservaORM.socio_id == filtro.socio_id)
        if filtro.libro_id is not None:
            condiciones.append(ReservaORM.libro_id == filtro.libro_id)
        if filtro.sede_id is not None:
            condiciones.append(ReservaORM.sede_retiro_id == filtro.sede_id)
        if filtro.estado is not None:
            condiciones.append(ReservaORM.estado == filtro.estado.value)
        total = self._sesion.scalar(select(func.count(ReservaORM.id)).where(*condiciones))
        filas = self._varios(
            select(ReservaORM)
            .where(*condiciones)
            .order_by(ReservaORM.fecha_reserva.desc(), ReservaORM.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return filas, total or 0

    def activas_de_sede(self, sede_id: int, limite: int) -> tuple[list[Reserva], int]:
        condiciones = [ReservaORM.sede_retiro_id == sede_id, ReservaORM.estado.in_(_ACTIVAS)]
        total = self._sesion.scalar(select(func.count(ReservaORM.id)).where(*condiciones))
        filas = self._varios(
            select(ReservaORM).where(*condiciones).order_by(ReservaORM.id).limit(limite)
        )
        return filas, total or 0

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, reserva: Reserva) -> None:
        orm = ReservaORM(
            numero=reserva.numero,
            socio_id=reserva.socio_id,
            libro_id=reserva.libro_id,
            sede_retiro_id=reserva.sede_retiro_id,
            fecha_reserva=reserva.fecha_reserva,
        )
        self._copiar(reserva, orm)
        try:
            with self._sesion.begin_nested():
                self._sesion.add(orm)
                self._sesion.flush()
        except IntegrityError as error:
            restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if restriccion != "uq_reserva_activa":
                raise
            raise ReservaDuplicada(
                "El socio ya tiene una reserva activa de este libro.",
                [{"campo": "libro_id", "problema": "reserva_duplicada"}],
            ) from error
        reserva.id = orm.id

    def guardar(self, reserva: Reserva) -> None:
        assert reserva.id is not None
        orm = self._sesion.get(ReservaORM, reserva.id)
        assert orm is not None
        self._copiar(reserva, orm)
        self._sesion.flush()

    # --- internos -------------------------------------------------------------------------

    @staticmethod
    def _copiar(reserva: Reserva, orm: ReservaORM) -> None:
        orm.estado = reserva.estado_nombre.value
        orm.ejemplar_id = reserva.ejemplar_id
        orm.prestamo_id = reserva.prestamo_id
        orm.vencimiento_retiro = reserva.vencimiento_retiro
        orm.fecha_cierre = reserva.fecha_cierre

    def _uno(self, consulta: Any) -> Reserva | None:
        filas = self._varios(consulta)
        return filas[0] if filas else None

    def _varios(self, consulta: Any) -> list[Reserva]:
        filas = list(self._sesion.scalars(consulta).unique())
        if not filas:
            return []
        titulos = dict(
            self._sesion.execute(
                select(LibroORM.id, LibroORM.titulo).where(
                    LibroORM.id.in_({f.libro_id for f in filas})
                )
            ).all()
        )
        reservas = [_a_dominio(f, titulos) for f in filas]
        for reserva in reservas:
            if reserva.estado_nombre == EstadoReservaEnum.PENDIENTE:
                reserva.posicion_en_cola = self._posicion(reserva)
        return reservas

    def _posicion(self, reserva: Reserva) -> int:
        """Lugar en la cola: pendientes del libro anteriores a esta, más uno (FIFO)."""
        anteriores = self._sesion.scalar(
            select(func.count(ReservaORM.id)).where(
                ReservaORM.libro_id == reserva.libro_id,
                ReservaORM.estado == _PENDIENTE,
                (ReservaORM.fecha_reserva < reserva.fecha_reserva)
                | (
                    (ReservaORM.fecha_reserva == reserva.fecha_reserva)
                    & (ReservaORM.id < (reserva.id or 0))
                ),
            )
        )
        return (anteriores or 0) + 1
