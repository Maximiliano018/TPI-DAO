"""Repositorios de devoluciones y multas sobre SQLAlchemy."""

from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.db.models import DevolucionORM, MultaORM, PagoORM
from app.models.devolucion import Devolucion, EstadoMulta, EstadoRecibido, Multa
from app.models.pago import EstadoPago, FormaEnLinea, MedioPago, Pago
from app.models.usuario import UsuarioRef
from app.repositories.impl.consultas import nombres_de_usuarios
from app.repositories.interfaces.devolucion_repository import FiltroMultas


class SqlAlchemyDevolucionRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def agregar(self, devolucion: Devolucion) -> None:
        orm = DevolucionORM(
            prestamo_id=devolucion.prestamo_id,
            sede_id=devolucion.sede_id,
            fecha_hora=devolucion.fecha_hora,
            estado_fisico_recibido=devolucion.estado_recibido.value,
            dias_atraso=devolucion.dias_atraso,
            observaciones=devolucion.observaciones,
            registrada_por_id=devolucion.registrada_por.id if devolucion.registrada_por else None,
            registrada_en=devolucion.registrada_en or devolucion.fecha_hora,
            motivo_fecha=devolucion.motivo_fecha,
        )
        self._sesion.add(orm)
        self._sesion.flush()
        devolucion.id = orm.id

    def de_prestamo(self, prestamo_id: int) -> Devolucion | None:
        orm = self._sesion.scalar(
            select(DevolucionORM).where(DevolucionORM.prestamo_id == prestamo_id)
        )
        if orm is None:
            return None
        nombres = nombres_de_usuarios(self._sesion, [orm.registrada_por_id or 0])
        return Devolucion(
            id=orm.id,
            prestamo_id=orm.prestamo_id,
            sede_id=orm.sede_id,
            fecha_hora=orm.fecha_hora,
            estado_recibido=EstadoRecibido(orm.estado_fisico_recibido),
            dias_atraso=orm.dias_atraso,
            observaciones=orm.observaciones,
            registrada_por=(
                UsuarioRef(orm.registrada_por_id, nombres.get(orm.registrada_por_id, ""))
                if orm.registrada_por_id
                else None
            ),
            registrada_en=orm.registrada_en,
            motivo_fecha=orm.motivo_fecha,
        )


def _multa_a_dominio(orm: MultaORM, nombres: dict[int, str]) -> Multa:
    prestamo = orm.prestamo
    return Multa(
        id=orm.id,
        prestamo_id=orm.prestamo_id,
        socio_id=orm.socio_id,
        dias_atraso=orm.dias_atraso,
        monto_por_dia=orm.monto_por_dia,
        monto_total=orm.monto_total,
        fecha_generacion=orm.fecha_generacion,
        estado=EstadoMulta(orm.estado),
        fecha_saldada=orm.fecha_saldada,
        saldada_por=(
            UsuarioRef(orm.saldada_por_id, nombres.get(orm.saldada_por_id, ""))
            if orm.saldada_por_id
            else None
        ),
        numero_prestamo=prestamo.numero,
        socio_nombre=f"{prestamo.socio.nombre} {prestamo.socio.apellido}",
        libro_titulo=prestamo.ejemplar.libro.titulo,
    )


class SqlAlchemyMultaRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def agregar(self, multa: Multa) -> None:
        orm = MultaORM(
            prestamo_id=multa.prestamo_id,
            socio_id=multa.socio_id,
            dias_atraso=multa.dias_atraso,
            monto_por_dia=multa.monto_por_dia,
            monto_total=multa.monto_total,
            estado=multa.estado.value,
            fecha_generacion=multa.fecha_generacion,
        )
        self._sesion.add(orm)
        self._sesion.flush()
        multa.id = orm.id

    def guardar(self, multa: Multa) -> None:
        assert multa.id is not None
        orm = self._sesion.get(MultaORM, multa.id)
        assert orm is not None
        orm.estado = multa.estado.value
        orm.fecha_saldada = multa.fecha_saldada
        orm.saldada_por_id = multa.saldada_por.id if multa.saldada_por else None
        self._sesion.flush()

    def obtener(self, multa_id: int) -> Multa | None:
        return self._uno(select(MultaORM).where(MultaORM.id == multa_id))

    def obtener_para_modificar(self, multa_id: int) -> Multa | None:
        return self._uno(
            select(MultaORM)
            .where(MultaORM.id == multa_id)
            .with_for_update(of=MultaORM)
            .execution_options(populate_existing=True)
        )

    def de_prestamo(self, prestamo_id: int) -> Multa | None:
        return self._uno(select(MultaORM).where(MultaORM.prestamo_id == prestamo_id))

    def listar(self, filtro: FiltroMultas, page: int, size: int) -> tuple[list[Multa], int]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.socio_id is not None:
            condiciones.append(MultaORM.socio_id == filtro.socio_id)
        if filtro.estado is not None:
            condiciones.append(MultaORM.estado == filtro.estado.value)
        total = self._sesion.scalar(select(func.count(MultaORM.id)).where(*condiciones))
        filas = self._varios(
            select(MultaORM)
            .where(*condiciones)
            .order_by(MultaORM.fecha_generacion.desc(), MultaORM.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return filas, total or 0

    def _uno(self, consulta: Any) -> Multa | None:
        filas = self._varios(consulta)
        return filas[0] if filas else None

    def _varios(self, consulta: Any) -> list[Multa]:
        filas = list(self._sesion.scalars(consulta).unique())
        nombres = nombres_de_usuarios(self._sesion, (f.saldada_por_id or 0 for f in filas))
        multas = [_multa_a_dominio(f, nombres) for f in filas]
        if multas:
            vigentes = self._sesion.scalars(
                select(PagoORM).where(
                    PagoORM.multa_id.in_([m.id for m in multas]),
                    PagoORM.estado.in_([EstadoPago.APROBADO.value, EstadoPago.PENDIENTE.value]),
                )
            ).all()
            refs = nombres_de_usuarios(self._sesion, (p.registrado_por_id or 0 for p in vigentes))
            por_multa = {m.id: m for m in multas}
            for orm in vigentes:
                pago = _pago_a_dominio(orm, refs)
                multa = por_multa[orm.multa_id]
                if pago.estado == EstadoPago.APROBADO:
                    multa.pago_aprobado = pago
                else:
                    multa.pago_pendiente = pago
        return multas


def _pago_a_dominio(orm: PagoORM, nombres: dict[int, str]) -> Pago:
    return Pago(
        id=orm.id,
        multa_id=orm.multa_id,
        medio=MedioPago(orm.medio),
        monto=orm.monto,
        estado=EstadoPago(orm.estado),
        fecha=orm.fecha,
        registrado_por=(
            UsuarioRef(orm.registrado_por_id, nombres.get(orm.registrado_por_id, ""))
            if orm.registrado_por_id
            else None
        ),
        comprobante=orm.comprobante,
        acreditado_en=orm.acreditado_en,
        motivo=orm.motivo,
        forma_en_linea=FormaEnLinea(orm.forma_en_linea) if orm.forma_en_linea else None,
        tarjeta_ultimos4=orm.tarjeta_ultimos4,
    )


class SqlAlchemyPagoRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def agregar(self, pago: Pago) -> None:
        orm = PagoORM(
            multa_id=pago.multa_id,
            medio=pago.medio.value,
            registrado_por_id=pago.registrado_por.id if pago.registrado_por else None,
            fecha=pago.fecha,
        )
        self._copiar(pago, orm)
        self._sesion.add(orm)
        self._sesion.flush()
        pago.id = orm.id

    def guardar(self, pago: Pago) -> None:
        assert pago.id is not None
        orm = self._sesion.get(PagoORM, pago.id)
        assert orm is not None
        self._copiar(pago, orm)
        self._sesion.flush()

    def obtener(self, pago_id: int) -> Pago | None:
        return self._uno(select(PagoORM).where(PagoORM.id == pago_id))

    def obtener_para_modificar(self, pago_id: int) -> Pago | None:
        return self._uno(self._bloqueado(select(PagoORM).where(PagoORM.id == pago_id)))

    def pendiente_de_multa(self, multa_id: int) -> Pago | None:
        return self._uno(
            self._bloqueado(
                select(PagoORM).where(
                    PagoORM.multa_id == multa_id, PagoORM.estado == EstadoPago.PENDIENTE.value
                )
            )
        )

    @staticmethod
    def _bloqueado(consulta: Any) -> Any:
        return consulta.with_for_update(of=PagoORM).execution_options(populate_existing=True)

    @staticmethod
    def _copiar(pago: Pago, orm: PagoORM) -> None:
        orm.estado = pago.estado.value
        orm.monto = pago.monto
        orm.comprobante = pago.comprobante
        orm.motivo = pago.motivo
        orm.acreditado_en = pago.acreditado_en
        orm.forma_en_linea = pago.forma_en_linea.value if pago.forma_en_linea else None
        orm.tarjeta_ultimos4 = pago.tarjeta_ultimos4

    def _uno(self, consulta: Any) -> Pago | None:
        filas = self._varios(consulta)
        return filas[0] if filas else None

    def _varios(self, consulta: Any) -> list[Pago]:
        filas = list(self._sesion.scalars(consulta))
        nombres = nombres_de_usuarios(self._sesion, (f.registrado_por_id or 0 for f in filas))
        pagos = [_pago_a_dominio(f, nombres) for f in filas]
        multas = {
            m.id: m
            for m in self._sesion.scalars(
                select(MultaORM).where(MultaORM.id.in_({p.multa_id for p in pagos}))
            ).unique()
        }
        for pago in pagos:
            multa = multas.get(pago.multa_id)
            if multa is None:
                continue
            prestamo = multa.prestamo
            pago.numero_prestamo = prestamo.numero
            pago.libro_titulo = prestamo.ejemplar.libro.titulo
            pago.dias_atraso = multa.dias_atraso
            pago.socio_nombre = f"{prestamo.socio.nombre} {prestamo.socio.apellido}"
            pago.numero_socio = prestamo.socio.numero_socio
        return pagos
