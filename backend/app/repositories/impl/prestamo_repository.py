"""Repositorios de préstamos, remitos, incidencias y parámetros sobre SQLAlchemy."""

from collections.abc import Iterable
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    DetalleRemitoORM,
    IncidenciaORM,
    MovimientoPrestamoORM,
    MovimientoRemitoORM,
    ParametroORM,
    PrestamoORM,
    RemitoORM,
    SedeORM,
)
from app.db.models.prestamo import SECUENCIA_PRESTAMO, SECUENCIA_REMITO
from app.models.ejemplar import EstadoFisico
from app.models.incidencia import Incidencia, OrigenIncidencia, TipoIncidencia
from app.models.parametros import Parametros
from app.models.prestamo import (
    MovimientoPrestamo,
    Prestamo,
    TipoPrestamo,
    formatear_numero,
)
from app.models.remito import (
    LineaRemito,
    MotivoRemito,
    MovimientoRemito,
    Remito,
    ResultadoLinea,
)
from app.models.states.prestamo import ABIERTOS as PRESTAMOS_ABIERTOS
from app.models.states.prestamo import EstadoPrestamoEnum, estado_prestamo
from app.models.states.remito import ABIERTOS as REMITOS_ABIERTOS
from app.models.states.remito import EstadoRemitoEnum, estado_remito
from app.models.usuario import UsuarioRef
from app.repositories.impl.consultas import nombres_de_usuarios
from app.repositories.interfaces.prestamo_repository import (
    FiltroPrestamos,
    FiltroRemitos,
    Parametro,
)

_ABIERTOS_P = [e.value for e in PRESTAMOS_ABIERTOS]
_ABIERTOS_R = [e.value for e in REMITOS_ABIERTOS]


def _refs(sesion: Session, ids: Iterable[int | None]) -> dict[int, str]:
    return nombres_de_usuarios(sesion, (i for i in ids if i is not None))


def _ref(nombres: dict[int, str], usuario_id: int | None) -> UsuarioRef | None:
    if usuario_id is None:
        return None
    return UsuarioRef(usuario_id, nombres.get(usuario_id, "Usuario eliminado"))


# --- parámetros ----------------------------------------------------------------------------------


class SqlAlchemyParametroRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def vigentes(self) -> Parametros:
        filas = self._sesion.scalars(select(ParametroORM))
        return Parametros.desde_textos({f.clave: f.valor for f in filas})

    def listar(self) -> list[Parametro]:
        filas = self._sesion.scalars(select(ParametroORM).order_by(ParametroORM.clave))
        return [Parametro(f.clave, f.valor, f.descripcion) for f in filas]

    def actualizar(self, clave: str, valor: str) -> Parametro | None:
        orm = self._sesion.get(ParametroORM, clave)
        if orm is None:
            return None
        orm.valor = valor
        self._sesion.flush()
        return Parametro(orm.clave, orm.valor, orm.descripcion)


# --- préstamos -----------------------------------------------------------------------------------


def _prestamo_a_dominio(orm: PrestamoORM, nombres: dict[int, str]) -> Prestamo:
    socio = orm.socio
    return Prestamo(
        id=orm.id,
        numero=orm.numero,
        tipo=TipoPrestamo(orm.tipo),
        socio_id=orm.socio_id,
        ejemplar_id=orm.ejemplar_id,
        libro_id=orm.ejemplar.libro_id,
        sede_origen_id=orm.sede_origen_id,
        sede_destino_id=orm.sede_destino_id,
        fecha_solicitud=orm.fecha_solicitud,
        registrado_por=_ref(nombres, orm.registrado_por_id),
        estado=estado_prestamo(orm.estado),
        fecha_inicio=orm.fecha_inicio,
        fecha_vencimiento=orm.fecha_vencimiento,
        fecha_devolucion=orm.fecha_devolucion,
        renovaciones=orm.renovaciones,
        fecha_limite_retiro=orm.fecha_limite_retiro,
        socio_nombre=f"{socio.nombre} {socio.apellido}",
        numero_socio=socio.numero_socio,
        codigo_ejemplar=orm.ejemplar.codigo_inventario,
        libro_titulo=orm.ejemplar.libro.titulo,
        sede_origen_nombre=orm.sede_origen.nombre,
        sede_destino_nombre=orm.sede_destino.nombre,
    )


class SqlAlchemyPrestamoRepository:
    """Implementa ``PrestamoRepository``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def siguiente_numero(self, anio: int) -> str:
        valor = self._sesion.scalar(SECUENCIA_PRESTAMO.next_value())
        assert valor is not None
        return formatear_numero("P", anio, int(valor))

    def obtener(self, prestamo_id: int) -> Prestamo | None:
        return self._uno(select(PrestamoORM).where(PrestamoORM.id == prestamo_id))

    def obtener_para_modificar(self, prestamo_id: int) -> Prestamo | None:
        return self._uno(
            select(PrestamoORM)
            .where(PrestamoORM.id == prestamo_id)
            .with_for_update(of=PrestamoORM)
            .execution_options(populate_existing=True)
        )

    def abiertos_de_socio(self, socio_id: int) -> list[Prestamo]:
        return self._varios(
            select(PrestamoORM).where(
                PrestamoORM.socio_id == socio_id, PrestamoORM.estado.in_(_ABIERTOS_P)
            )
        )

    def activos_vencidos(self, hoy: date) -> list[Prestamo]:
        return self._varios(
            select(PrestamoORM)
            .where(
                PrestamoORM.estado == EstadoPrestamoEnum.ACTIVO.value,
                PrestamoORM.fecha_vencimiento < hoy,
            )
            .order_by(PrestamoORM.id)
            .with_for_update(of=PrestamoORM)
        )

    def retiros_vencidos(self, hoy: date) -> list[Prestamo]:
        return self._varios(
            select(PrestamoORM)
            .where(
                PrestamoORM.estado.in_(
                    [EstadoPrestamoEnum.SOLICITADO.value, EstadoPrestamoEnum.EN_ENVIO.value]
                ),
                PrestamoORM.fecha_limite_retiro < hoy,
            )
            .order_by(PrestamoORM.id)
            .with_for_update(of=PrestamoORM)
        )

    def listar(self, filtro: FiltroPrestamos, page: int, size: int) -> tuple[list[Prestamo], int]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.estado is not None:
            condiciones.append(PrestamoORM.estado == filtro.estado.value)
        if filtro.tipo is not None:
            condiciones.append(PrestamoORM.tipo == filtro.tipo.value)
        if filtro.socio_id is not None:
            condiciones.append(PrestamoORM.socio_id == filtro.socio_id)
        if filtro.sede_id is not None:
            condiciones.append(
                (PrestamoORM.sede_origen_id == filtro.sede_id)
                | (PrestamoORM.sede_destino_id == filtro.sede_id)
            )
        if filtro.numero:
            condiciones.append(PrestamoORM.numero.contains(filtro.numero.upper(), autoescape=True))
        if filtro.sede_origen_id is not None:
            condiciones.append(PrestamoORM.sede_origen_id == filtro.sede_origen_id)
        total = self._sesion.scalar(select(func.count(PrestamoORM.id)).where(*condiciones))
        filas = self._varios(
            select(PrestamoORM)
            .where(*condiciones)
            .order_by(PrestamoORM.fecha_solicitud.desc(), PrestamoORM.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return filas, total or 0

    def historial(self, prestamo_id: int) -> list[MovimientoPrestamo]:
        filas = list(
            self._sesion.scalars(
                select(MovimientoPrestamoORM)
                .where(MovimientoPrestamoORM.prestamo_id == prestamo_id)
                .order_by(MovimientoPrestamoORM.fecha_hora, MovimientoPrestamoORM.id)
            )
        )
        nombres = _refs(self._sesion, (f.usuario_id for f in filas))
        return [
            MovimientoPrestamo(
                EstadoPrestamoEnum(f.estado_anterior) if f.estado_anterior else None,
                EstadoPrestamoEnum(f.estado_nuevo),
                f.fecha_hora,
                _ref(nombres, f.usuario_id),
                f.observacion,
            )
            for f in filas
        ]

    def en_curso_de_sede(self, sede_id: int, limite: int) -> tuple[list[Prestamo], int]:
        condiciones = [
            PrestamoORM.estado.in_(_ABIERTOS_P),
            (PrestamoORM.sede_origen_id == sede_id) | (PrestamoORM.sede_destino_id == sede_id),
        ]
        total = self._sesion.scalar(select(func.count(PrestamoORM.id)).where(*condiciones))
        filas = self._varios(
            select(PrestamoORM).where(*condiciones).order_by(PrestamoORM.id).limit(limite)
        )
        return filas, total or 0

    def agregar(self, prestamo: Prestamo) -> None:
        orm = PrestamoORM(
            numero=prestamo.numero,
            socio_id=prestamo.socio_id,
            ejemplar_id=prestamo.ejemplar_id,
            tipo=prestamo.tipo.value,
            sede_origen_id=prestamo.sede_origen_id,
            sede_destino_id=prestamo.sede_destino_id,
            fecha_solicitud=prestamo.fecha_solicitud,
            registrado_por_id=prestamo.registrado_por.id if prestamo.registrado_por else None,
        )
        self._copiar(prestamo, orm)
        self._sesion.add(orm)
        self._sesion.flush()
        prestamo.id = orm.id
        self._movimientos(prestamo)

    def guardar(self, prestamo: Prestamo) -> None:
        assert prestamo.id is not None
        orm = self._sesion.get(PrestamoORM, prestamo.id)
        assert orm is not None
        self._copiar(prestamo, orm)
        self._movimientos(prestamo)

    @staticmethod
    def _copiar(prestamo: Prestamo, orm: PrestamoORM) -> None:
        orm.estado = prestamo.estado_nombre.value
        orm.fecha_inicio = prestamo.fecha_inicio
        orm.fecha_vencimiento = prestamo.fecha_vencimiento
        orm.fecha_devolucion = prestamo.fecha_devolucion
        orm.renovaciones = prestamo.renovaciones
        orm.fecha_limite_retiro = prestamo.fecha_limite_retiro

    def _movimientos(self, prestamo: Prestamo) -> None:
        assert prestamo.id is not None
        for mov in prestamo.movimientos_pendientes:
            self._sesion.add(
                MovimientoPrestamoORM(
                    prestamo_id=prestamo.id,
                    estado_anterior=mov.estado_anterior.value if mov.estado_anterior else None,
                    estado_nuevo=mov.estado_nuevo.value,
                    fecha_hora=mov.fecha_hora,
                    usuario_id=mov.usuario.id if mov.usuario else None,
                    observacion=mov.observacion,
                )
            )
        prestamo.movimientos_pendientes.clear()
        self._sesion.flush()

    def _uno(self, consulta: Any) -> Prestamo | None:
        filas = self._varios(consulta)
        return filas[0] if filas else None

    def _varios(self, consulta: Any) -> list[Prestamo]:
        filas = list(self._sesion.scalars(consulta).unique())
        nombres = _refs(self._sesion, (f.registrado_por_id for f in filas))
        return [_prestamo_a_dominio(f, nombres) for f in filas]


# --- remitos -------------------------------------------------------------------------------------


def _remito_a_dominio(orm: RemitoORM) -> Remito:
    lineas = [
        LineaRemito(
            ejemplar_id=d.ejemplar_id,
            prestamo_id=d.prestamo_id,
            estado_fisico_salida=EstadoFisico(d.estado_fisico_salida),
            estado_fisico_llegada=(
                EstadoFisico(d.estado_fisico_llegada) if d.estado_fisico_llegada else None
            ),
            resultado=ResultadoLinea(d.resultado) if d.resultado else None,
            observacion=d.observacion,
            codigo_ejemplar=d.ejemplar.codigo_inventario,
            libro_titulo=d.ejemplar.libro.titulo,
        )
        for d in orm.lineas
    ]
    return Remito(
        id=orm.id,
        numero=orm.numero,
        sede_origen_id=orm.sede_origen_id,
        sede_destino_id=orm.sede_destino_id,
        motivo=MotivoRemito(orm.motivo),
        lineas=lineas,
        estado=estado_remito(orm.estado),
        fecha_generacion=orm.fecha_generacion,
        fecha_despacho=orm.fecha_despacho,
        fecha_recepcion=orm.fecha_recepcion,
        observaciones=orm.observaciones,
        version=orm.version,
        sede_origen_nombre=orm.sede_origen.nombre,
        sede_destino_nombre=orm.sede_destino.nombre,
    )


class SqlAlchemyRemitoRepository:
    """Implementa ``RemitoRepository``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def siguiente_numero(self, anio: int) -> str:
        valor = self._sesion.scalar(SECUENCIA_REMITO.next_value())
        assert valor is not None
        return formatear_numero("R", anio, int(valor))

    def obtener(self, remito_id: int) -> Remito | None:
        orm = self._sesion.get(RemitoORM, remito_id)
        return _remito_a_dominio(orm) if orm else None

    def obtener_para_modificar(self, remito_id: int) -> Remito | None:
        orm = self._sesion.scalars(
            select(RemitoORM)
            .where(RemitoORM.id == remito_id)
            .with_for_update(of=RemitoORM)
            .execution_options(populate_existing=True)
        ).first()
        return _remito_a_dominio(orm) if orm else None

    def listar(self, filtro: FiltroRemitos, page: int, size: int) -> tuple[list[Remito], int]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.estado is not None:
            condiciones.append(RemitoORM.estado == filtro.estado.value)
        if filtro.solo_abiertos:
            condiciones.append(RemitoORM.estado.in_(_ABIERTOS_R))
        if filtro.motivo is not None:
            condiciones.append(RemitoORM.motivo == filtro.motivo.value)
        if filtro.sede_id is not None:
            condiciones.append(
                (RemitoORM.sede_origen_id == filtro.sede_id)
                | (RemitoORM.sede_destino_id == filtro.sede_id)
            )
        if filtro.numero:
            condiciones.append(RemitoORM.numero.contains(filtro.numero.upper(), autoescape=True))
        if filtro.generado_antes_de is not None:
            condiciones.append(
                RemitoORM.estado.in_(
                    [EstadoRemitoEnum.GENERADO.value, EstadoRemitoEnum.EMPAQUETADO.value]
                )
            )
            condiciones.append(RemitoORM.fecha_generacion < filtro.generado_antes_de)
        total = self._sesion.scalar(select(func.count(RemitoORM.id)).where(*condiciones))
        filas = self._sesion.scalars(
            select(RemitoORM)
            .where(*condiciones)
            .order_by(RemitoORM.fecha_generacion.desc(), RemitoORM.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return [_remito_a_dominio(f) for f in filas], total or 0

    def historial(self, remito_id: int) -> list[MovimientoRemito]:
        filas = list(
            self._sesion.scalars(
                select(MovimientoRemitoORM)
                .where(MovimientoRemitoORM.remito_id == remito_id)
                .order_by(MovimientoRemitoORM.fecha_hora, MovimientoRemitoORM.id)
            )
        )
        nombres = _refs(self._sesion, (f.usuario_id for f in filas))
        return [
            MovimientoRemito(
                EstadoRemitoEnum(f.estado_anterior) if f.estado_anterior else None,
                EstadoRemitoEnum(f.estado_nuevo),
                f.fecha_hora,
                _ref(nombres, f.usuario_id),
                f.observacion,
            )
            for f in filas
        ]

    def abierto_con_ejemplar(self, ejemplar_id: int) -> Remito | None:
        orm = self._sesion.scalars(
            select(RemitoORM)
            .join(DetalleRemitoORM, DetalleRemitoORM.remito_id == RemitoORM.id)
            .where(DetalleRemitoORM.ejemplar_id == ejemplar_id, RemitoORM.estado.in_(_ABIERTOS_R))
        ).first()
        return _remito_a_dominio(orm) if orm else None

    def de_prestamo(self, prestamo_id: int) -> list[Remito]:
        filas = self._sesion.scalars(
            select(RemitoORM)
            .join(DetalleRemitoORM, DetalleRemitoORM.remito_id == RemitoORM.id)
            .where(DetalleRemitoORM.prestamo_id == prestamo_id)
            .order_by(RemitoORM.fecha_generacion, RemitoORM.id)
        )
        return [_remito_a_dominio(f) for f in filas]

    def abiertos_de_sede(self, sede_id: int, limite: int) -> tuple[list[Remito], int]:
        condiciones = [
            RemitoORM.estado.in_(_ABIERTOS_R),
            (RemitoORM.sede_origen_id == sede_id) | (RemitoORM.sede_destino_id == sede_id),
        ]
        total = self._sesion.scalar(select(func.count(RemitoORM.id)).where(*condiciones))
        filas = self._sesion.scalars(
            select(RemitoORM).where(*condiciones).order_by(RemitoORM.id).limit(limite)
        )
        return [_remito_a_dominio(f) for f in filas], total or 0

    def agregar(self, remito: Remito) -> None:
        orm = RemitoORM(
            numero=remito.numero,
            sede_origen_id=remito.sede_origen_id,
            sede_destino_id=remito.sede_destino_id,
            motivo=remito.motivo.value,
            fecha_generacion=remito.fecha_generacion,
        )
        self._copiar(remito, orm)
        orm.lineas = [
            DetalleRemitoORM(
                ejemplar_id=linea.ejemplar_id,
                prestamo_id=linea.prestamo_id,
                estado_fisico_salida=linea.estado_fisico_salida.value,
            )
            for linea in remito.lineas
        ]
        self._sesion.add(orm)
        self._sesion.flush()
        remito.id = orm.id
        self._movimientos(remito)

    def guardar(self, remito: Remito) -> None:
        assert remito.id is not None
        orm = self._sesion.get(RemitoORM, remito.id)
        assert orm is not None
        self._copiar(remito, orm)
        por_ejemplar = {d.ejemplar_id: d for d in orm.lineas}
        for linea in remito.lineas:
            detalle = por_ejemplar[linea.ejemplar_id]
            detalle.estado_fisico_llegada = (
                linea.estado_fisico_llegada.value if linea.estado_fisico_llegada else None
            )
            detalle.resultado = linea.resultado.value if linea.resultado else None
            detalle.observacion = linea.observacion
        self._movimientos(remito)

    @staticmethod
    def _copiar(remito: Remito, orm: RemitoORM) -> None:
        orm.estado = remito.estado_nombre.value
        orm.fecha_despacho = remito.fecha_despacho
        orm.fecha_recepcion = remito.fecha_recepcion
        orm.observaciones = remito.observaciones
        orm.version = remito.version

    def _movimientos(self, remito: Remito) -> None:
        assert remito.id is not None
        for mov in remito.movimientos_pendientes:
            self._sesion.add(
                MovimientoRemitoORM(
                    remito_id=remito.id,
                    estado_anterior=mov.estado_anterior.value if mov.estado_anterior else None,
                    estado_nuevo=mov.estado_nuevo.value,
                    fecha_hora=mov.fecha_hora,
                    usuario_id=mov.usuario.id if mov.usuario else None,
                    observacion=mov.observacion,
                )
            )
        remito.movimientos_pendientes.clear()
        self._sesion.flush()


# --- incidencias ---------------------------------------------------------------------------------


class SqlAlchemyIncidenciaRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def agregar(self, incidencia: Incidencia) -> None:
        orm = IncidenciaORM(
            tipo=incidencia.tipo.value,
            origen=incidencia.origen.value,
            ejemplar_id=incidencia.ejemplar_id,
            socio_id=incidencia.socio_id,
            prestamo_id=incidencia.prestamo_id,
            remito_id=incidencia.remito_id,
            sede_responsable_id=incidencia.sede_responsable_id,
            descripcion=incidencia.descripcion,
            fecha=incidencia.fecha,
            usuario_id=incidencia.usuario.id if incidencia.usuario else None,
        )
        self._sesion.add(orm)
        self._sesion.flush()
        incidencia.id = orm.id

    def guardar(self, incidencia: Incidencia) -> None:
        assert incidencia.id is not None
        orm = self._sesion.get(IncidenciaORM, incidencia.id)
        assert orm is not None
        orm.resuelta_en = incidencia.resuelta_en
        orm.resuelta_por_id = incidencia.resuelta_por.id if incidencia.resuelta_por else None
        orm.resolucion = incidencia.resolucion
        self._sesion.flush()

    def de_remito(self, remito_id: int) -> list[Incidencia]:
        return self._varias(
            select(IncidenciaORM)
            .where(IncidenciaORM.remito_id == remito_id)
            .order_by(IncidenciaORM.id)
        )

    def extravio_pendiente(self, ejemplar_id: int) -> Incidencia | None:
        filas = self._varias(
            select(IncidenciaORM)
            .where(
                IncidenciaORM.ejemplar_id == ejemplar_id,
                IncidenciaORM.tipo == TipoIncidencia.EXTRAVIO.value,
                IncidenciaORM.resuelta_en.is_(None),
            )
            .order_by(IncidenciaORM.fecha.desc(), IncidenciaORM.id.desc())
            .limit(1)
            .with_for_update(of=IncidenciaORM)
        )
        return filas[0] if filas else None

    def _varias(self, consulta: Any) -> list[Incidencia]:
        filas = list(self._sesion.scalars(consulta))
        nombres = _refs(
            self._sesion,
            (u for f in filas for u in (f.usuario_id, f.resuelta_por_id)),
        )
        sedes_ids = {f.sede_responsable_id for f in filas if f.sede_responsable_id is not None}
        sedes = (
            dict(
                self._sesion.execute(
                    select(SedeORM.id, SedeORM.nombre).where(SedeORM.id.in_(sedes_ids))
                ).all()
            )
            if sedes_ids
            else {}
        )
        return [
            Incidencia(
                tipo=TipoIncidencia(f.tipo),
                origen=OrigenIncidencia(f.origen),
                ejemplar_id=f.ejemplar_id,
                descripcion=f.descripcion,
                fecha=f.fecha,
                usuario=_ref(nombres, f.usuario_id),
                socio_id=f.socio_id,
                prestamo_id=f.prestamo_id,
                remito_id=f.remito_id,
                sede_responsable_id=f.sede_responsable_id,
                id=f.id,
                resuelta_en=f.resuelta_en,
                resuelta_por=_ref(nombres, f.resuelta_por_id),
                resolucion=f.resolucion,
                sede_responsable_nombre=(
                    sedes.get(f.sede_responsable_id) if f.sede_responsable_id else None
                ),
            )
            for f in filas
        ]
