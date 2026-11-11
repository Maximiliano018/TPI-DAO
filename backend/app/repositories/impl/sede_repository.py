"""Repositorios de sedes y del catálogo geográfico sobre SQLAlchemy."""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    ExcepcionHorarioSedeORM,
    HistorialSedeORM,
    HorarioSedeORM,
    LocalidadORM,
    ProvinciaORM,
    SedeORM,
)
from app.exceptions import SedeCodigoDuplicado, SedeNoEncontrada, SedeNombreDuplicado
from app.models.horario import ExcepcionHorario, TipoExcepcion
from app.models.sede import (
    MENSAJE_NO_DISPONIBLE,
    Cambio,
    DatosBaja,
    EstadoSede,
    EventoSede,
    Sede,
    TipoEventoSede,
)
from app.models.usuario import UsuarioRef
from app.models.valores import (
    CodigoSede,
    Contacto,
    Direccion,
    Email,
    FranjaHoraria,
    Localidad,
    Telefono,
)
from app.repositories.impl.consultas import nombres_de_usuarios, sin_tildes
from app.repositories.interfaces.sede_repository import (
    FiltroEstado,
    FiltroHistorial,
    FiltroSedes,
    OrdenSedes,
)

_ORDEN: dict[OrdenSedes, tuple[Any, bool]] = {
    OrdenSedes.NOMBRE: (SedeORM.nombre_normalizado, False),
    OrdenSedes.NOMBRE_DESC: (SedeORM.nombre_normalizado, True),
    OrdenSedes.CODIGO: (SedeORM.codigo, False),
    OrdenSedes.CODIGO_DESC: (SedeORM.codigo, True),
    OrdenSedes.CREADO_EN: (SedeORM.creado_en, False),
    OrdenSedes.CREADO_EN_DESC: (SedeORM.creado_en, True),
}


def _localidad_a_dominio(orm: LocalidadORM) -> Localidad:
    return Localidad(
        id=orm.id,
        nombre=orm.nombre,
        departamento=orm.departamento,
        provincia_id=orm.provincia_id,
        provincia=orm.provincia.nombre,
    )


def _ids_de_usuarios(sedes: Iterable[SedeORM]) -> set[int]:
    ids: set[int] = set()
    for sede in sedes:
        ids.update((sede.creado_por_id, sede.actualizado_por_id))
        if sede.baja_por_id is not None:
            ids.add(sede.baja_por_id)
    return ids


def _a_dominio(orm: SedeORM, nombres: dict[int, str]) -> Sede:
    def ref(usuario_id: int) -> UsuarioRef:
        return UsuarioRef(usuario_id, nombres.get(usuario_id, "Usuario eliminado"))

    baja = None
    if orm.estado == EstadoSede.BAJA.value and orm.fecha_baja and orm.baja_por_id:
        baja = DatosBaja(orm.fecha_baja, orm.motivo_baja or "", ref(orm.baja_por_id))
    return Sede(
        id=orm.id,
        codigo=CodigoSede(orm.codigo),
        nombre=orm.nombre,
        direccion=Direccion(orm.calle, orm.numero, _localidad_a_dominio(orm.localidad)),
        contacto=Contacto(Telefono(orm.telefono), Email(orm.email), orm.responsable),
        horarios=[
            FranjaHoraria(h.dia_semana, h.hora_apertura, h.hora_cierre) for h in orm.horarios
        ],
        estado=EstadoSede(orm.estado),
        version=orm.version,
        creado_en=orm.creado_en,
        creado_por=ref(orm.creado_por_id),
        actualizado_en=orm.actualizado_en,
        actualizado_por=ref(orm.actualizado_por_id),
        excepciones=[
            ExcepcionHorario(
                fecha=e.fecha,
                tipo=TipoExcepcion(e.tipo),
                desde=e.hora_desde,
                hasta=e.hora_hasta,
                motivo=e.motivo,
                id=e.id,
            )
            for e in orm.excepciones
        ],
        baja=baja,
    )


def _traducir_duplicado(error: IntegrityError) -> Exception | None:
    """Convierte la violación de una restricción única de sede en su error de negocio."""
    restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if restriccion == "uq_sede_codigo":
        return SedeCodigoDuplicado(
            "Ya existe una sede con ese código.", [{"campo": "codigo", "problema": "duplicado"}]
        )
    if restriccion == "uq_sede_nombre_normalizado":
        return SedeNombreDuplicado(
            "Ya existe una sede con ese nombre.", [{"campo": "nombre", "problema": "duplicado"}]
        )
    return None


class SqlAlchemySedeRepository:
    """Implementa ``SedeRepository`` con SQLAlchemy y bloqueos de fila de PostgreSQL."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, sede: Sede) -> None:
        with self._escritura():
            orm = SedeORM(
                codigo=sede.codigo.valor,
                creado_por_id=sede.creado_por.id,
                creado_en=sede.creado_en,
            )
            self._copiar_datos(sede, orm)
            orm.horarios = [self._horario_orm(h) for h in sede.horarios]
            self._sesion.add(orm)
            self._sesion.flush()
            sede.id = orm.id
            self._persistir_excepciones(sede, orm)
            self._persistir_eventos(sede)

    def guardar(self, sede: Sede) -> None:
        assert sede.id is not None
        with self._escritura():
            orm = self._sesion.get(SedeORM, sede.id)
            if orm is None:
                raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
            self._copiar_datos(sede, orm)
            self._sincronizar_horarios(sede, orm)
            self._persistir_excepciones(sede, orm)
            self._persistir_eventos(sede)

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, sede_id: int) -> Sede | None:
        return self._cargar(select(SedeORM).where(SedeORM.id == sede_id))

    def obtener_para_modificar(self, sede_id: int) -> Sede | None:
        consulta = (
            select(SedeORM)
            .where(SedeORM.id == sede_id)
            .with_for_update(of=SedeORM)
            .execution_options(populate_existing=True)
        )
        return self._cargar(consulta)

    def obtener_para_operar(self, sede_id: int) -> Sede:
        consulta = (
            select(SedeORM)
            .where(SedeORM.id == sede_id)
            .with_for_update(read=True, of=SedeORM)
            .execution_options(populate_existing=True)
        )
        sede = self._cargar(consulta)
        if sede is None:
            raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
        sede.validar_operativa()
        return sede

    def buscar_por_codigo(self, codigo: str) -> Sede | None:
        return self._cargar(select(SedeORM).where(SedeORM.codigo == codigo))

    def buscar_por_nombre_normalizado(
        self, nombre_normalizado: str, excluir_id: int | None = None
    ) -> Sede | None:
        consulta = select(SedeORM).where(SedeORM.nombre_normalizado == nombre_normalizado)
        if excluir_id is not None:
            consulta = consulta.where(SedeORM.id != excluir_id)
        return self._cargar(consulta)

    def buscar_por_direccion(
        self, direccion_normalizada: str, excluir_id: int | None = None
    ) -> list[Sede]:
        consulta = select(SedeORM).where(SedeORM.direccion_normalizada == direccion_normalizada)
        if excluir_id is not None:
            consulta = consulta.where(SedeORM.id != excluir_id)
        return self._cargar_varias(consulta.order_by(SedeORM.nombre_normalizado))

    def listar(self, filtro: FiltroSedes, page: int, size: int) -> tuple[list[Sede], int]:
        condiciones = self._condiciones(filtro)
        total = self._sesion.scalar(
            select(func.count(SedeORM.id)).join(SedeORM.localidad).where(*condiciones)
        )
        columna, descendente = _ORDEN[filtro.orden]
        orden = columna.desc() if descendente else columna.asc()
        consulta = (
            select(SedeORM)
            .join(SedeORM.localidad)
            .where(*condiciones)
            .order_by(orden, SedeORM.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        return self._cargar_varias(consulta), total or 0

    def contar_por_estado(self) -> dict[str, int]:
        filas = self._sesion.execute(select(SedeORM.estado, func.count()).group_by(SedeORM.estado))
        conteo = {estado.value: 0 for estado in EstadoSede}
        conteo.update({estado: cantidad for estado, cantidad in filas})
        return conteo

    def historial(
        self, sede_id: int, filtro: FiltroHistorial, page: int, size: int
    ) -> tuple[list[EventoSede], int]:
        condiciones: list[ColumnElement[bool]] = [HistorialSedeORM.sede_id == sede_id]
        if filtro.tipo_evento is not None:
            condiciones.append(HistorialSedeORM.tipo_evento == filtro.tipo_evento.value)
        if filtro.desde is not None:
            condiciones.append(HistorialSedeORM.fecha_hora >= filtro.desde)
        if filtro.hasta is not None:
            condiciones.append(HistorialSedeORM.fecha_hora <= filtro.hasta)
        total = self._sesion.scalar(select(func.count(HistorialSedeORM.id)).where(*condiciones))
        filas = self._sesion.scalars(
            select(HistorialSedeORM)
            .where(*condiciones)
            .order_by(HistorialSedeORM.fecha_hora.desc(), HistorialSedeORM.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        nombres = nombres_de_usuarios(self._sesion, (f.usuario_id for f in filas))
        return [self._evento_a_dominio(f, nombres) for f in filas], total or 0

    # --- internos: lectura ----------------------------------------------------------------

    def _cargar(self, consulta: Any) -> Sede | None:
        orm = self._sesion.scalars(self._con_relaciones(consulta)).unique().first()
        if orm is None:
            return None
        return _a_dominio(orm, nombres_de_usuarios(self._sesion, _ids_de_usuarios([orm])))

    def _cargar_varias(self, consulta: Any) -> list[Sede]:
        filas = self._sesion.scalars(self._con_relaciones(consulta)).unique().all()
        nombres = nombres_de_usuarios(self._sesion, _ids_de_usuarios(filas))
        return [_a_dominio(orm, nombres) for orm in filas]

    @staticmethod
    def _con_relaciones(consulta: Any) -> Any:
        return consulta.options(selectinload(SedeORM.horarios), selectinload(SedeORM.excepciones))

    @staticmethod
    def _condiciones(filtro: FiltroSedes) -> list[ColumnElement[bool]]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.estado != FiltroEstado.TODAS:
            condiciones.append(SedeORM.estado == filtro.estado.value)
        if filtro.localidad_id is not None:
            condiciones.append(SedeORM.localidad_id == filtro.localidad_id)
        if filtro.texto:
            condiciones.append(
                SedeORM.nombre_normalizado.contains(filtro.texto, autoescape=True)
                | func.lower(SedeORM.codigo).contains(filtro.texto, autoescape=True)
                | sin_tildes(SedeORM.calle).contains(filtro.texto, autoescape=True)
                | sin_tildes(LocalidadORM.nombre).contains(filtro.texto, autoescape=True)
            )
        return condiciones

    @staticmethod
    def _evento_a_dominio(orm: HistorialSedeORM, nombres: dict[int, str]) -> EventoSede:
        return EventoSede(
            id=orm.id,
            tipo=TipoEventoSede(orm.tipo_evento),
            usuario=UsuarioRef(orm.usuario_id, nombres.get(orm.usuario_id, "Usuario eliminado")),
            fecha_hora=orm.fecha_hora,
            version_resultante=orm.version_resultante,
            cambios=[Cambio(c["campo"], c.get("antes"), c.get("despues")) for c in orm.cambios],
            estado_anterior=EstadoSede(orm.estado_anterior) if orm.estado_anterior else None,
            estado_nuevo=EstadoSede(orm.estado_nuevo) if orm.estado_nuevo else None,
            motivo=orm.motivo,
        )

    # --- internos: escritura --------------------------------------------------------------

    @contextmanager
    def _escritura(self) -> Iterator[None]:
        """Agrupa las escrituras en un savepoint y traduce las violaciones de unicidad.

        Todo el trabajo va dentro del bloque: ``begin_nested`` envía antes lo pendiente, y un
        fallo ahí invalidaría la transacción entera. Así, ante un duplicado solo se deshace el
        savepoint y la sesión sigue utilizable para que el servicio haga su ``rollback``.
        """
        try:
            with self._sesion.begin_nested():
                yield
                self._sesion.flush()
        except IntegrityError as error:
            traducido = _traducir_duplicado(error)
            if traducido is None:
                raise
            raise traducido from error

    @staticmethod
    def _copiar_datos(sede: Sede, orm: SedeORM) -> None:
        orm.nombre = sede.nombre
        orm.nombre_normalizado = sede.nombre_normalizado
        orm.calle = sede.direccion.calle
        orm.numero = sede.direccion.numero
        orm.localidad_id = sede.direccion.localidad.id
        orm.direccion_normalizada = sede.direccion.normalizada()
        orm.telefono = sede.contacto.telefono.valor
        orm.email = sede.contacto.email.valor
        orm.responsable = sede.contacto.responsable
        orm.estado = sede.estado.value
        orm.fecha_baja = sede.baja.fecha if sede.baja else None
        orm.motivo_baja = sede.baja.motivo if sede.baja else None
        orm.baja_por_id = sede.baja.usuario.id if sede.baja else None
        orm.version = sede.version
        orm.actualizado_en = sede.actualizado_en
        orm.actualizado_por_id = sede.actualizado_por.id

    @staticmethod
    def _horario_orm(franja: FranjaHoraria) -> HorarioSedeORM:
        return HorarioSedeORM(
            dia_semana=franja.dia, hora_apertura=franja.apertura, hora_cierre=franja.cierre
        )

    def _sincronizar_horarios(self, sede: Sede, orm: SedeORM) -> None:
        actuales = {(h.dia_semana, h.hora_apertura, h.hora_cierre) for h in orm.horarios}
        nuevos = {(f.dia, f.apertura, f.cierre) for f in sede.horarios}
        if actuales == nuevos:
            return
        # Se borran y se vacían antes de insertar: la restricción de exclusión de la base
        # rechazaría franjas nuevas que se superpongan con las que todavía existen.
        orm.horarios.clear()
        self._sesion.flush()
        orm.horarios.extend(self._horario_orm(f) for f in sede.horarios)
        self._sesion.flush()

    def _persistir_excepciones(self, sede: Sede, orm: SedeORM) -> None:
        conservadas = {e.id for e in sede.excepciones if e.id is not None}
        for existente in list(orm.excepciones):
            if existente.id not in conservadas:
                orm.excepciones.remove(existente)
        nuevas: list[tuple[int, ExcepcionHorarioSedeORM]] = []
        for posicion, excepcion in enumerate(sede.excepciones):
            if excepcion.id is not None:
                continue
            fila = ExcepcionHorarioSedeORM(
                fecha=excepcion.fecha,
                tipo=excepcion.tipo.value,
                hora_desde=excepcion.desde,
                hora_hasta=excepcion.hasta,
                motivo=excepcion.motivo,
                creado_por_id=sede.actualizado_por.id,
            )
            orm.excepciones.append(fila)
            nuevas.append((posicion, fila))
        self._sesion.flush()
        for posicion, fila in nuevas:
            sede.excepciones[posicion] = replace(sede.excepciones[posicion], id=fila.id)

    def _persistir_eventos(self, sede: Sede) -> None:
        assert sede.id is not None
        filas = [
            HistorialSedeORM(
                sede_id=sede.id,
                tipo_evento=evento.tipo.value,
                fecha_hora=evento.fecha_hora,
                usuario_id=evento.usuario.id,
                estado_anterior=evento.estado_anterior.value if evento.estado_anterior else None,
                estado_nuevo=evento.estado_nuevo.value if evento.estado_nuevo else None,
                motivo=evento.motivo,
                cambios=[c.como_dict() for c in evento.cambios],
                version_resultante=evento.version_resultante,
            )
            for evento in sede.eventos_pendientes
        ]
        self._sesion.add_all(filas)
        self._sesion.flush()
        for evento, fila in zip(sede.eventos_pendientes, filas, strict=True):
            evento.id = fila.id
        sede.eventos_pendientes.clear()


class SqlAlchemyLocalidadRepository:
    """Implementa ``LocalidadRepository`` sobre el catálogo cerrado."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def obtener(self, localidad_id: int) -> Localidad | None:
        orm = self._sesion.get(LocalidadORM, localidad_id)
        return _localidad_a_dominio(orm) if orm else None

    def listar(self, provincia_id: int | None = None, texto: str | None = None) -> list[Localidad]:
        consulta = select(LocalidadORM)
        if provincia_id is not None:
            consulta = consulta.where(LocalidadORM.provincia_id == provincia_id)
        if texto:
            consulta = consulta.where(
                sin_tildes(LocalidadORM.nombre).contains(texto, autoescape=True)
            )
        filas = self._sesion.scalars(
            # Collation "C" sobre el texto sin tildes: mismo orden en cualquier servidor.
            consulta.order_by(sin_tildes(LocalidadORM.nombre).collate("C"), LocalidadORM.id)
        ).all()
        return [_localidad_a_dominio(f) for f in filas]

    def provincias(self) -> list[tuple[int, str]]:
        filas = self._sesion.execute(
            select(ProvinciaORM.id, ProvinciaORM.nombre).order_by("nombre")
        )
        return [(fila.id, fila.nombre) for fila in filas]
