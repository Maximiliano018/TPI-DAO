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
from app.models.devolucion import concepto_de_multa
from app.models.policies.multa import TipoMulta
from app.models.usuario import Permiso, Rol, Usuario
from app.models.valores import error_de_campo
from app.repositories.impl.catalogo_repository import (
    columnas_de_disponibilidad,
    condiciones_de_disponibilidad,
    condiciones_de_libros,
)
from app.repositories.impl.prestamo_repository import SqlAlchemyParametroRepository
from app.repositories.interfaces.catalogo_repository import FiltroLibros
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
from app.utils.texto import normalizar

RECIBIDOS = ("RECIBIDO", "DANADO", "DESTRUIDO", "INCOMPLETO")
CERRADOS = (*RECIBIDOS, "EXTRAVIADO")
REMITOS_ABIERTOS = ("GENERADO", "EMPAQUETADO", "DESPACHADO", "EN_TRANSITO")
PRESTAMOS_AFUERA = ("ACTIVO", "VENCIDO")
FALTANTE = "FALTANTE"
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
        sede_origen_id: int | None = None,
        sede_destino_id: int | None = None,
        motivo: str | None = None,
    ) -> MovimientoEntreSedes:
        """Por ruta origen → destino: envíos, ejemplares y tránsito promedio (RF-REP-01).

        Solo cuentan los remitos que llegaron (con o sin incidencias): los que siguen en camino
        no entran en el promedio (CA-REP-02). El tránsito es recepción − despacho. Los
        ejemplares son los que llegaron: los faltantes no cuentan como movidos (CA-REP-17).
        ``sede_id`` es la sede que interviene (origen o destino); ``sede_origen_id``,
        ``sede_destino_id`` y ``motivo`` acotan la ruta (CA-REP-16).
        """
        actor.exigir(Permiso.REPORTE_SEDE)
        self._validar_periodo(desde, hasta)
        sede_id = self._alcance(actor, sede_id)
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        llegados = func.count(
            case((DetalleRemitoORM.resultado.is_distinct_from(FALTANTE), DetalleRemitoORM.id))
        )
        lineas = (
            select(DetalleRemitoORM.remito_id, llegados.label("n"))
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
        if sede_origen_id is not None:
            condiciones.append(RemitoORM.sede_origen_id == sede_origen_id)
        if sede_destino_id is not None:
            condiciones.append(RemitoORM.sede_destino_id == sede_destino_id)
        if motivo is not None:
            condiciones.append(RemitoORM.motivo == motivo)
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
        """Tasa de envíos exitosos e incidencias, total y por sede origen y destino (RF-REP-02).

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
            _contar(RemitoORM.estado == "INCOMPLETO"),
        )
        total = self._sesion.execute(select(*conteos).where(*condiciones)).one()

        def por(columna_sede: Any) -> list[EnviosDeSede]:
            filas = self._sesion.execute(
                select(SedeORM.id, SedeORM.nombre, *conteos)
                .join(SedeORM, SedeORM.id == columna_sede)
                .where(*condiciones)
                .group_by(SedeORM.id, SedeORM.nombre)
                .order_by(SedeORM.nombre)
            ).all()
            return [EnviosDeSede(**_conteo(f[2:]), sede_id=f[0], sede=f[1]) for f in filas]

        return EnviosEIncidencias(
            **_conteo(total),
            desde=desde,
            hasta=hasta,
            por_sede=por(RemitoORM.sede_origen_id),
            por_destino=por(RemitoORM.sede_destino_id),
        )

    # --- R3 -------------------------------------------------------------------------------

    def libros_mas_solicitados(
        self,
        actor: Usuario,
        desde: date | None = None,
        hasta: date | None = None,
        categoria_id: int | None = None,
        limite: int = 10,
        sede_id: int | None = None,
    ) -> LibrosMasSolicitados:
        """Ranking por préstamos interbibliotecarios no cancelados (RF-REP-03, CA-REP-06/07).

        ``sede_id`` deja los préstamos en los que la sede interviene, como origen o destino
        (CA-REP-16).
        """
        actor.exigir(Permiso.REPORTE_RED)
        self._validar_periodo(desde, hasta)
        condiciones = [
            PrestamoORM.tipo == "INTERBIBLIOTECARIO",
            PrestamoORM.estado != "CANCELADO",
            *self._en_periodo(PrestamoORM.fecha_solicitud, desde, hasta),
        ]
        if categoria_id is not None:
            condiciones.append(LibroORM.categoria_id == categoria_id)
        if sede_id is not None:
            condiciones.append(_interviene(PrestamoORM, sede_id))

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
        atraso_min: int | None = None,
        atraso_max: int | None = None,
    ) -> VencidosYMultas:
        """Préstamos vencidos con su multa acumulada a hoy y las multas generadas (RF-REP-04).

        La multa acumulada usa el monto por día y el tope vigentes (la definitiva se fija al
        devolver). La sede y el socio definen el alcance; la sede interviene como origen o
        destino del préstamo, igual que en R6 (CA-REP-19). El estado de la multa, el período
        (fecha de generación de la multa) y el rango de atraso solo acotan las listas: los
        totales son siempre la deuda real del alcance (CA-REP-18). Las multas por daño o
        extravío no tienen atraso: un rango de atraso las deja fuera de la lista.
        """
        actor.exigir(Permiso.REPORTE_SEDE)
        self._validar_periodo(desde, hasta)
        if atraso_min is not None and atraso_max is not None and atraso_max < atraso_min:
            raise error_de_campo("atraso_max", "El atraso máximo no puede ser menor que el mínimo.")
        sede_id = self._alcance(actor, sede_id)
        hoy = self._reloj.hoy()
        parametros = SqlAlchemyParametroRepository(self._sesion).vigentes()
        todos = self._vencidos(sede_id, socio_id, hoy, parametros.politica_multa())
        vencidos = [v for v in todos if _en_rango(v.dias_atraso, atraso_min, atraso_max)]
        multas = self._multas(sede_id, socio_id, estado_multa, desde, hasta, atraso_min, atraso_max)
        acumulado = sum((v.multa_acumulada for v in todos), Decimal("0.00"))
        pendientes = self._deuda_en_multas(sede_id, socio_id)
        return VencidosYMultas(
            fecha=hoy,
            monto_por_dia=parametros.multa_por_dia,
            vencidos=vencidos,
            multas=multas,
            cantidad_vencidos=len(todos),
            total_acumulado_vencidos=acumulado,
            total_multas_pendientes=pendientes,
            total_adeudado=acumulado + pendientes,
        )

    def _vencidos(
        self, sede_id: int | None, socio_id: int | None, hoy: date, politica: Any
    ) -> list[PrestamoVencido]:
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        condiciones = [
            PrestamoORM.estado.in_(PRESTAMOS_AFUERA),
            PrestamoORM.fecha_vencimiento < hoy,
            *_alcance_de_prestamos(sede_id, socio_id),
        ]
        filas: Sequence[Any] = self._sesion.execute(
            select(
                PrestamoORM.id,
                PrestamoORM.numero,
                SocioORM.id,
                SocioORM.nombre,
                SocioORM.apellido,
                SocioORM.numero_socio,
                LibroORM.titulo,
                destino.nombre,
                origen.nombre,
                PrestamoORM.fecha_vencimiento,
            )
            .join(SocioORM, SocioORM.id == PrestamoORM.socio_id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .join(destino, destino.id == PrestamoORM.sede_destino_id)
            .join(origen, origen.id == PrestamoORM.sede_origen_id)
            .where(*condiciones)
            .order_by(PrestamoORM.fecha_vencimiento, PrestamoORM.numero)
        ).all()
        vencidos = []
        for f in filas:
            dias = (hoy - f[9]).days
            vencidos.append(
                PrestamoVencido(
                    prestamo_id=f[0],
                    numero=f[1],
                    socio_id=f[2],
                    socio=f"{f[3]} {f[4]}",
                    numero_socio=f[5],
                    libro=f[6],
                    sede=f[7],
                    sede_origen=f[8],
                    fecha_vencimiento=f[9],
                    dias_atraso=dias,
                    multa_acumulada=politica.calcular(dias),
                )
            )
        return vencidos

    def _deuda_en_multas(self, sede_id: int | None, socio_id: int | None) -> Decimal:
        """Suma de las multas pendientes del alcance, sin los filtros de la lista."""
        total = self._sesion.scalar(
            select(func.coalesce(func.sum(MultaORM.monto_total), 0))
            .join(PrestamoORM, PrestamoORM.id == MultaORM.prestamo_id)
            .where(MultaORM.estado == "PENDIENTE", *_alcance_de_prestamos(sede_id, socio_id))
        )
        return Decimal(total or 0).quantize(Decimal("0.01"))

    def _multas(
        self,
        sede_id: int | None,
        socio_id: int | None,
        estado: str | None,
        desde: date | None,
        hasta: date | None,
        atraso_min: int | None,
        atraso_max: int | None,
    ) -> list[MultaDelReporte]:
        condiciones = [
            *self._en_periodo(MultaORM.fecha_generacion, desde, hasta),
            *_alcance_de_prestamos(sede_id, socio_id),
        ]
        if estado is not None:
            condiciones.append(MultaORM.estado == estado)
        if atraso_min is not None:
            condiciones.append(MultaORM.dias_atraso >= atraso_min)
        if atraso_max is not None:
            condiciones.append(MultaORM.dias_atraso <= atraso_max)
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
                MultaORM.tipo,
            )
            .join(PrestamoORM, PrestamoORM.id == MultaORM.prestamo_id)
            .join(SocioORM, SocioORM.id == MultaORM.socio_id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .where(*condiciones)
            .order_by(MultaORM.estado, MultaORM.fecha_generacion.desc())
        ).all()
        return [
            MultaDelReporte(
                multa_id=f[0],
                prestamo_id=f[1],
                numero_prestamo=f[2],
                socio_id=f[3],
                socio=f"{f[4]} {f[5]}",
                libro=f[6],
                tipo=f[11],
                concepto=concepto_de_multa(TipoMulta(f[11]), f[7]),
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
        texto: str | None = None,
    ) -> DisponibilidadPorSede:
        """Ejemplares activos por libro y sede propietaria, según su estado (RF-REP-05).

        Cuenta igual que la ficha del libro (CA-REP-20). ``texto`` busca en el título, los
        autores y el ISBN, como el catálogo (CA-REP-16).
        """
        actor.exigir(Permiso.CATALOGO_LEER)
        filtro = FiltroLibros(
            texto=normalizar(texto) if texto and texto.strip() else None,
            categoria_id=categoria_id,
        )
        condiciones = [*condiciones_de_disponibilidad(), *condiciones_de_libros(filtro)]
        if sede_id is not None:
            condiciones.append(EjemplarORM.sede_propietaria_id == sede_id)
        if libro_id is not None:
            condiciones.append(EjemplarORM.libro_id == libro_id)
        grupos = (LibroORM.id, LibroORM.titulo, SedeORM.id, SedeORM.nombre)
        consulta = (
            select(*grupos, *columnas_de_disponibilidad())
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
        self,
        actor: Usuario,
        sede_id: int | None = None,
        estado: str | None = None,
        tipo: str | None = None,
        estado_remito: str | None = None,
    ) -> ActivosYEnTransito:
        """Préstamos en manos de socios y remitos abiertos con su antigüedad (RF-REP-06).

        ``estado`` separa los préstamos al día (``ACTIVO``) de los vencidos (``VENCIDO``) por su
        fecha de vencimiento, igual que R4, aunque la tarea diaria todavía no los haya marcado.
        ``tipo`` filtra los préstamos y ``estado_remito``, los remitos (CA-REP-16).
        """
        actor.exigir(Permiso.REPORTE_SEDE)
        sede_id = self._alcance(actor, sede_id)
        hoy = self._reloj.hoy()
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        condiciones: list[ColumnElement[bool]] = [PrestamoORM.estado.in_(PRESTAMOS_AFUERA)]
        if sede_id is not None:
            condiciones.append(_interviene(PrestamoORM, sede_id))
        if estado == "VENCIDO":
            condiciones.append(PrestamoORM.fecha_vencimiento < hoy)
        elif estado == "ACTIVO":
            condiciones.append(PrestamoORM.fecha_vencimiento >= hoy)
        if tipo is not None:
            condiciones.append(PrestamoORM.tipo == tipo)
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
        remitos = self._remitos_abiertos(sede_id, hoy, estado_remito)
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

    def _remitos_abiertos(
        self, sede_id: int | None, hoy: date, estado: str | None
    ) -> list[RemitoAbierto]:
        origen, destino = aliased(SedeORM), aliased(SedeORM)
        condiciones: list[ColumnElement[bool]] = [RemitoORM.estado.in_(REMITOS_ABIERTOS)]
        if sede_id is not None:
            condiciones.append(_interviene(RemitoORM, sede_id))
        if estado is not None:
            condiciones.append(RemitoORM.estado == estado)
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
    claves = ("total_envios", "recibidos", "extraviados", "danados", "destruidos", "incompletos")
    return {clave: int(valor) for clave, valor in zip(claves, fila, strict=True)}


def _interviene(modelo: Any, sede_id: int) -> ColumnElement[bool]:
    return or_(modelo.sede_origen_id == sede_id, modelo.sede_destino_id == sede_id)


def _alcance_de_prestamos(sede_id: int | None, socio_id: int | None) -> list[ColumnElement[bool]]:
    """Préstamos de la sede (como origen o destino) y del socio, si se indican."""
    condiciones = []
    if sede_id is not None:
        condiciones.append(_interviene(PrestamoORM, sede_id))
    if socio_id is not None:
        condiciones.append(PrestamoORM.socio_id == socio_id)
    return condiciones


def _en_rango(valor: int, minimo: int | None, maximo: int | None) -> bool:
    return (minimo is None or valor >= minimo) and (maximo is None or valor <= maximo)
