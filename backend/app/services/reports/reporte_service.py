"""Reportes R1 a R6 (proceso obligatorio 9).

Son consultas de solo lectura con SQL agregado (``GROUP BY``) sobre los datos que registran los
procesos: remitos y su historial, préstamos, multas y ejemplares. No recorren entidades una por
una ni guardan nada. El bibliotecario queda limitado a su sede (CU-REP-01, A4).
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db.models import (
    DetalleRemitoORM,
    EjemplarORM,
    LibroORM,
    MultaORM,
    PrestamoORM,
    RemitoORM,
    SedeORM,
    SocioORM,
)
from app.models.usuario import Permiso, Rol, Usuario
from app.models.valores import error_de_campo
from app.repositories.impl.prestamo_repository import SqlAlchemyParametroRepository
from app.services.reports.resultados import (
    ActivosYEnTransito,
    DisponibilidadLibroSede,
    DisponibilidadPorSede,
    EnviosDeSede,
    EnviosEIncidencias,
    LibrosMasSolicitados,
    LibroSolicitado,
    MovimientoEntreSedes,
    MultaDelReporte,
    PrestamoEnCurso,
    PrestamoVencido,
    RemitoAbierto,
    RutaEntreSedes,
    VencidosYMultas,
)
from app.utils.reloj import Reloj

RECIBIDOS = ("RECIBIDO", "DANADO", "DESTRUIDO")
CERRADOS = (*RECIBIDOS, "EXTRAVIADO")
REMITOS_ABIERTOS = ("GENERADO", "EMPAQUETADO", "DESPACHADO", "EN_TRANSITO")
PRESTAMOS_AFUERA = ("ACTIVO", "VENCIDO")
SEGUNDOS_POR_DIA = 86400


def _contar(condicion: ColumnElement[bool]) -> Any:
    return func.count(case((condicion, 1)))


class ReporteService:
    """Emite los reportes; cada método valida permisos y filtros antes de consultar."""

    def __init__(self, sesion: Session, reloj: Reloj) -> None:
        self._sesion = sesion
        self._reloj = reloj

    # --- R1 -------------------------------------------------------------------------------

    def movimiento_entre_sedes(
        self,
        actor: Usuario,
        desde: date | None = None,
        hasta: date | None = None,
        sede_id: int | None = None,
    ) -> MovimientoEntreSedes:
        """Por ruta origen → destino: envíos, ejemplares y tránsito promedio (RF-REP-01).

        Solo cuentan los remitos que llegaron (con o sin incidencias): los que siguen en camino
        no entran en el promedio (CA-REP-02). El tránsito es recepción − despacho.
        """
        actor.exigir(Permiso.REPORTE_SEDE)
        self._validar_periodo(desde, hasta)
        sede_id = self._alcance(actor, sede_id)
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        lineas = (
            select(DetalleRemitoORM.remito_id, func.count(DetalleRemitoORM.id).label("n"))
            .group_by(DetalleRemitoORM.remito_id)
            .subquery()
        )
        transito = func.extract("epoch", RemitoORM.fecha_recepcion - RemitoORM.fecha_despacho)
        condiciones = [
            RemitoORM.estado.in_(RECIBIDOS),
            RemitoORM.fecha_despacho.is_not(None),
            RemitoORM.fecha_recepcion.is_not(None),
            *self._en_periodo(RemitoORM.fecha_recepcion, desde, hasta),
        ]
        if sede_id is not None:
            condiciones.append(_interviene(RemitoORM, sede_id))
        filas: Sequence[Any] = self._sesion.execute(
            select(
                origen.id,
                origen.nombre,
                destino.id,
                destino.nombre,
                func.count(RemitoORM.id),
                func.coalesce(func.sum(lineas.c.n), 0),
                func.avg(transito),
            )
            .join(origen, origen.id == RemitoORM.sede_origen_id)
            .join(destino, destino.id == RemitoORM.sede_destino_id)
            .join(lineas, lineas.c.remito_id == RemitoORM.id)
            .where(*condiciones)
            .group_by(origen.id, origen.nombre, destino.id, destino.nombre)
            .order_by(func.count(RemitoORM.id).desc(), origen.nombre, destino.nombre)
        ).all()
        rutas = [
            RutaEntreSedes(
                sede_origen_id=f[0],
                sede_origen=f[1],
                sede_destino_id=f[2],
                sede_destino=f[3],
                envios=f[4],
                ejemplares=int(f[5]),
                tiempo_promedio_transito_dias=round(float(f[6]) / SEGUNDOS_POR_DIA, 1),
            )
            for f in filas
        ]
        return MovimientoEntreSedes(
            desde=desde,
            hasta=hasta,
            rutas=rutas,
            total_envios=sum(r.envios for r in rutas),
            total_ejemplares=sum(r.ejemplares for r in rutas),
        )

    # --- R2 -------------------------------------------------------------------------------

    def envios_e_incidencias(
        self,
        actor: Usuario,
        desde: date | None = None,
        hasta: date | None = None,
        sede_id: int | None = None,
    ) -> EnviosEIncidencias:
        """Tasa de envíos exitosos e incidencias, total y por sede origen (RF-REP-02).

        Cuenta los remitos cerrados despachados en el período; los anulados y los que siguen
        abiertos no entran (CA-REP-05).
        """
        actor.exigir(Permiso.REPORTE_RED)
        self._validar_periodo(desde, hasta)
        condiciones = [
            RemitoORM.estado.in_(CERRADOS),
            *self._en_periodo(RemitoORM.fecha_despacho, desde, hasta),
        ]
        if sede_id is not None:
            condiciones.append(_interviene(RemitoORM, sede_id))
        conteos = (
            func.count(RemitoORM.id),
            _contar(RemitoORM.estado == "RECIBIDO"),
            _contar(RemitoORM.estado == "EXTRAVIADO"),
            _contar(RemitoORM.estado == "DANADO"),
            _contar(RemitoORM.estado == "DESTRUIDO"),
        )
        total = self._sesion.execute(select(*conteos).where(*condiciones)).one()
        por_sede = self._sesion.execute(
            select(SedeORM.id, SedeORM.nombre, *conteos)
            .join(SedeORM, SedeORM.id == RemitoORM.sede_origen_id)
            .where(*condiciones)
            .group_by(SedeORM.id, SedeORM.nombre)
            .order_by(SedeORM.nombre)
        ).all()
        return EnviosEIncidencias(
            **_conteo(total),
            desde=desde,
            hasta=hasta,
            por_sede=[EnviosDeSede(**_conteo(f[2:]), sede_id=f[0], sede=f[1]) for f in por_sede],
        )

    # --- R3 -------------------------------------------------------------------------------

    def libros_mas_solicitados(
        self,
        actor: Usuario,
        desde: date | None = None,
        hasta: date | None = None,
        categoria_id: int | None = None,
        limite: int = 10,
    ) -> LibrosMasSolicitados:
        """Ranking por préstamos interbibliotecarios no cancelados (RF-REP-03, CA-REP-06/07)."""
        actor.exigir(Permiso.REPORTE_RED)
        self._validar_periodo(desde, hasta)
        condiciones = [
            PrestamoORM.tipo == "INTERBIBLIOTECARIO",
            PrestamoORM.estado != "CANCELADO",
            *self._en_periodo(PrestamoORM.fecha_solicitud, desde, hasta),
        ]
        if categoria_id is not None:
            condiciones.append(LibroORM.categoria_id == categoria_id)

        def base(*columnas: Any) -> Any:
            return (
                select(*columnas)
                .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
                .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
                .where(*condiciones)
            )

        cantidad = func.count(PrestamoORM.id)
        ranking = self._sesion.execute(
            base(LibroORM.id, LibroORM.titulo, cantidad)
            .group_by(LibroORM.id, LibroORM.titulo)
            .order_by(cantidad.desc(), LibroORM.titulo)
            .limit(limite)
        ).all()
        ids = [f[0] for f in ranking]
        origenes = self._mas_frecuente(base, ids, PrestamoORM.sede_origen_id)
        destinos = self._mas_frecuente(base, ids, PrestamoORM.sede_destino_id)
        return LibrosMasSolicitados(
            desde=desde,
            hasta=hasta,
            libros=[
                LibroSolicitado(
                    posicion=i,
                    libro_id=f[0],
                    titulo=f[1],
                    prestamos=f[2],
                    sede_origen_frecuente=origenes.get(f[0]),
                    sede_destino_frecuente=destinos.get(f[0]),
                )
                for i, f in enumerate(ranking, start=1)
            ],
        )

    def _mas_frecuente(self, base: Any, libros: Sequence[int], sede: Any) -> dict[int, str]:
        """Sede más frecuente de cada libro (en empate, la primera por nombre)."""
        if not libros:
            return {}
        filas: Sequence[Any] = self._sesion.execute(
            base(LibroORM.id, SedeORM.nombre, func.count(PrestamoORM.id))
            .join(SedeORM, SedeORM.id == sede)
            .where(LibroORM.id.in_(libros))
            .group_by(LibroORM.id, SedeORM.nombre)
        ).all()
        mejores: dict[int, tuple[int, str]] = {}
        for fila in filas:
            libro_id, nombre, cantidad = int(fila[0]), str(fila[1]), int(fila[2])
            actual = mejores.get(libro_id)
            if actual is None or (-cantidad, nombre) < (-actual[0], actual[1]):
                mejores[libro_id] = (cantidad, nombre)
        return {libro_id: nombre for libro_id, (_, nombre) in mejores.items()}

    # --- R4 -------------------------------------------------------------------------------

    def vencidos_y_multas(
        self,
        actor: Usuario,
        sede_id: int | None = None,
        socio_id: int | None = None,
        estado_multa: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> VencidosYMultas:
        """Préstamos vencidos con su multa acumulada a hoy y las multas generadas (RF-REP-04).

        La multa acumulada usa el monto por día vigente (la definitiva se fija al devolver). El
        período filtra las multas por su fecha de generación.
        """
        actor.exigir(Permiso.REPORTE_SEDE)
        self._validar_periodo(desde, hasta)
        sede_id = self._alcance(actor, sede_id)
        hoy = self._reloj.hoy()
        monto = SqlAlchemyParametroRepository(self._sesion).vigentes().multa_por_dia
        sede = aliased(SedeORM)
        condiciones: list[ColumnElement[bool]] = [
            PrestamoORM.estado.in_(PRESTAMOS_AFUERA),
            PrestamoORM.fecha_vencimiento < hoy,
        ]
        if sede_id is not None:
            condiciones.append(PrestamoORM.sede_destino_id == sede_id)
        if socio_id is not None:
            condiciones.append(PrestamoORM.socio_id == socio_id)
        filas: Sequence[Any] = self._sesion.execute(
            select(
                PrestamoORM.id,
                PrestamoORM.numero,
                SocioORM.id,
                SocioORM.nombre,
                SocioORM.apellido,
                SocioORM.numero_socio,
                LibroORM.titulo,
                sede.nombre,
                PrestamoORM.fecha_vencimiento,
            )
            .join(SocioORM, SocioORM.id == PrestamoORM.socio_id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .join(sede, sede.id == PrestamoORM.sede_destino_id)
            .where(*condiciones)
            .order_by(PrestamoORM.fecha_vencimiento, PrestamoORM.numero)
        ).all()
        vencidos = []
        for f in filas:
            vence: date = f[8]
            dias = (hoy - vence).days
            vencidos.append(
                PrestamoVencido(
                    prestamo_id=f[0],
                    numero=f[1],
                    socio_id=f[2],
                    socio=f"{f[3]} {f[4]}",
                    numero_socio=f[5],
                    libro=f[6],
                    sede=f[7],
                    fecha_vencimiento=f[8],
                    dias_atraso=dias,
                    multa_acumulada=(monto * dias).quantize(Decimal("0.01")),
                )
            )
        multas = self._multas(sede_id, socio_id, estado_multa, desde, hasta)
        acumulado = sum((v.multa_acumulada for v in vencidos), Decimal("0.00"))
        pendientes = sum(
            (m.monto_total for m in multas if m.estado == "PENDIENTE"), Decimal("0.00")
        )
        return VencidosYMultas(
            fecha=hoy,
            monto_por_dia=monto,
            vencidos=vencidos,
            multas=multas,
            total_acumulado_vencidos=acumulado,
            total_multas_pendientes=pendientes,
            total_adeudado=acumulado + pendientes,
        )

    def _multas(
        self,
        sede_id: int | None,
        socio_id: int | None,
        estado: str | None,
        desde: date | None,
        hasta: date | None,
    ) -> list[MultaDelReporte]:
        condiciones = list(self._en_periodo(MultaORM.fecha_generacion, desde, hasta))
        if sede_id is not None:
            condiciones.append(PrestamoORM.sede_destino_id == sede_id)
        if socio_id is not None:
            condiciones.append(MultaORM.socio_id == socio_id)
        if estado is not None:
            condiciones.append(MultaORM.estado == estado)
        filas: Sequence[Any] = self._sesion.execute(
            select(
                MultaORM.id,
                PrestamoORM.id,
                PrestamoORM.numero,
                SocioORM.id,
                SocioORM.nombre,
                SocioORM.apellido,
                LibroORM.titulo,
                MultaORM.dias_atraso,
                MultaORM.monto_total,
                MultaORM.estado,
                MultaORM.fecha_generacion,
            )
            .join(PrestamoORM, PrestamoORM.id == MultaORM.prestamo_id)
            .join(SocioORM, SocioORM.id == MultaORM.socio_id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .where(*condiciones)
            .order_by(MultaORM.estado.desc(), MultaORM.fecha_generacion.desc())
        ).all()
        return [
            MultaDelReporte(
                multa_id=f[0],
                prestamo_id=f[1],
                numero_prestamo=f[2],
                socio_id=f[3],
                socio=f"{f[4]} {f[5]}",
                libro=f[6],
                dias_atraso=f[7],
                monto_total=f[8],
                estado=f[9],
                fecha_generacion=f[10],
            )
            for f in filas
        ]

    # --- R5 -------------------------------------------------------------------------------

    def disponibilidad_por_sede(
        self,
        actor: Usuario,
        sede_id: int | None = None,
        libro_id: int | None = None,
        categoria_id: int | None = None,
        page: int = 1,
        size: int = 50,
    ) -> DisponibilidadPorSede:
        """Ejemplares activos por libro y sede propietaria, según su estado (RF-REP-05)."""
        actor.exigir(Permiso.CATALOGO_LEER)
        condiciones: list[ColumnElement[bool]] = [
            EjemplarORM.estado != "BAJA",
            SedeORM.estado == "ACTIVA",
        ]
        if sede_id is not None:
            condiciones.append(EjemplarORM.sede_propietaria_id == sede_id)
        if libro_id is not None:
            condiciones.append(EjemplarORM.libro_id == libro_id)
        if categoria_id is not None:
            condiciones.append(LibroORM.categoria_id == categoria_id)
        grupos = (LibroORM.id, LibroORM.titulo, SedeORM.id, SedeORM.nombre)
        consulta = (
            select(
                *grupos,
                func.count(EjemplarORM.id),
                _contar(EjemplarORM.estado == "DISPONIBLE"),
                _contar(EjemplarORM.estado == "PRESTADO"),
                _contar(EjemplarORM.estado.in_(("RESERVADO", "APARTADO"))),
                _contar(EjemplarORM.estado == "EN_TRANSITO"),
            )
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .join(SedeORM, SedeORM.id == EjemplarORM.sede_propietaria_id)
            .where(*condiciones)
            .group_by(*grupos)
        )
        total = self._sesion.scalar(select(func.count()).select_from(consulta.subquery()))
        filas: Sequence[Any] = self._sesion.execute(
            consulta.order_by(LibroORM.titulo, SedeORM.nombre).offset((page - 1) * size).limit(size)
        ).all()
        items = [
            DisponibilidadLibroSede(
                libro_id=f[0],
                titulo=f[1],
                sede_id=f[2],
                sede=f[3],
                totales=f[4],
                disponibles=f[5],
                prestados=f[6],
                reservados=f[7],
                en_transito=f[8],
                otros=f[4] - f[5] - f[6] - f[7] - f[8],
            )
            for f in filas
        ]
        return DisponibilidadPorSede(items, total or 0, page, size)

    # --- R6 -------------------------------------------------------------------------------

    def activos_y_en_transito(
        self, actor: Usuario, sede_id: int | None = None
    ) -> ActivosYEnTransito:
        """Préstamos en manos de socios y remitos abiertos con su antigüedad (RF-REP-06)."""
        actor.exigir(Permiso.REPORTE_SEDE)
        sede_id = self._alcance(actor, sede_id)
        hoy = self._reloj.hoy()
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        condiciones: list[ColumnElement[bool]] = [PrestamoORM.estado.in_(PRESTAMOS_AFUERA)]
        if sede_id is not None:
            condiciones.append(_interviene(PrestamoORM, sede_id))
        prestamos: Sequence[Any] = self._sesion.execute(
            select(
                PrestamoORM.id,
                PrestamoORM.numero,
                PrestamoORM.tipo,
                PrestamoORM.estado,
                SocioORM.nombre,
                SocioORM.apellido,
                LibroORM.titulo,
                origen.nombre,
                destino.nombre,
                PrestamoORM.fecha_vencimiento,
            )
            .join(SocioORM, SocioORM.id == PrestamoORM.socio_id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .join(origen, origen.id == PrestamoORM.sede_origen_id)
            .join(destino, destino.id == PrestamoORM.sede_destino_id)
            .where(*condiciones)
            .order_by(PrestamoORM.fecha_vencimiento, PrestamoORM.numero)
        ).all()
        remitos = self._remitos_abiertos(sede_id, hoy)
        return ActivosYEnTransito(
            fecha=hoy,
            prestamos=[
                PrestamoEnCurso(
                    prestamo_id=f[0],
                    numero=f[1],
                    tipo=f[2],
                    estado=f[3],
                    socio=f"{f[4]} {f[5]}",
                    libro=f[6],
                    sede_origen=f[7],
                    sede_destino=f[8],
                    fecha_vencimiento=f[9],
                    dias_para_vencer=(f[9] - hoy).days if f[9] else None,
                )
                for f in prestamos
            ],
            remitos=remitos,
        )

    def _remitos_abiertos(self, sede_id: int | None, hoy: date) -> list[RemitoAbierto]:
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        condiciones: list[ColumnElement[bool]] = [RemitoORM.estado.in_(REMITOS_ABIERTOS)]
        if sede_id is not None:
            condiciones.append(_interviene(RemitoORM, sede_id))
        lineas = func.count(DetalleRemitoORM.id)
        filas: Sequence[Any] = self._sesion.execute(
            select(
                RemitoORM.id,
                RemitoORM.numero,
                RemitoORM.motivo,
                RemitoORM.estado,
                origen.nombre,
                destino.nombre,
                RemitoORM.fecha_generacion,
                lineas,
            )
            .join(origen, origen.id == RemitoORM.sede_origen_id)
            .join(destino, destino.id == RemitoORM.sede_destino_id)
            .outerjoin(DetalleRemitoORM, DetalleRemitoORM.remito_id == RemitoORM.id)
            .where(*condiciones)
            .group_by(RemitoORM.id, origen.nombre, destino.nombre)
            .order_by(RemitoORM.fecha_generacion)
        ).all()
        zona = self._reloj.ahora_local().tzinfo
        return [
            RemitoAbierto(
                remito_id=f[0],
                numero=f[1],
                motivo=f[2],
                estado=f[3],
                sede_origen=f[4],
                sede_destino=f[5],
                fecha_generacion=f[6],
                antiguedad_dias=(hoy - f[6].astimezone(zona).date()).days,
                ejemplares=f[7],
            )
            for f in filas
        ]

    # --- internos -------------------------------------------------------------------------

    @staticmethod
    def _alcance(actor: Usuario, sede_id: int | None) -> int | None:
        """El bibliotecario ve solo su sede, aunque pida otra (CU-REP-01, A4)."""
        return actor.sede_id if actor.rol == Rol.BIBLIOTECARIO else sede_id

    @staticmethod
    def _validar_periodo(desde: date | None, hasta: date | None) -> None:
        if desde is not None and hasta is not None and hasta < desde:
            raise error_de_campo("hasta", "La fecha final no puede ser anterior a la inicial.")

    def _en_periodo(
        self, columna: Any, desde: date | None, hasta: date | None
    ) -> list[ColumnElement[bool]]:
        """Días completos en la zona de negocio, ``hasta`` inclusive."""
        zona = self._reloj.ahora_local().tzinfo
        condiciones = []
        if desde is not None:
            condiciones.append(columna >= datetime.combine(desde, time.min, zona))
        if hasta is not None:
            fin = datetime.combine(hasta + timedelta(days=1), time.min, zona)
            condiciones.append(columna < fin)
        return condiciones


def _conteo(fila: Sequence[Any]) -> dict[str, int]:
    claves = ("total_envios", "recibidos", "extraviados", "danados", "destruidos")
    return {clave: int(valor) for clave, valor in zip(claves, fila, strict=True)}


def _interviene(modelo: Any, sede_id: int) -> ColumnElement[bool]:
    return or_(modelo.sede_origen_id == sede_id, modelo.sede_destino_id == sede_id)
