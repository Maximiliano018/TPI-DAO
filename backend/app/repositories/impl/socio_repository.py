"""Repositorio de socios sobre SQLAlchemy."""

from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import PrestamoORM, SocioORM, UsuarioORM
from app.db.models.socio import SECUENCIA_NUMERO_SOCIO
from app.exceptions import DuplicadoError
from app.models.socio import (
    CuentaSocio,
    DatosPersonales,
    Documento,
    EstadoSocio,
    MotivoInhabilitacion,
    SituacionSocio,
    Socio,
    TipoDocumento,
    formatear_numero_socio,
)
from app.models.usuario import UsuarioRef
from app.models.valores import Email, Telefono
from app.repositories.impl.consultas import nombres_de_usuarios, sin_tildes
from app.repositories.interfaces.socio_repository import FiltroSocios


def _a_dominio(orm: SocioORM, nombres: dict[int, str], cuenta: UsuarioORM | None = None) -> Socio:
    def ref(usuario_id: int | None) -> UsuarioRef | None:
        if usuario_id is None:
            return None
        return UsuarioRef(usuario_id, nombres.get(usuario_id, "Usuario eliminado"))

    causas: set[MotivoInhabilitacion] = set()
    if orm.motivo_inhabilitacion:
        causas.add(MotivoInhabilitacion(orm.motivo_inhabilitacion))
    if orm.inhabilitacion_administrativa:
        causas.add(MotivoInhabilitacion.ADMINISTRATIVA)
    datos = DatosPersonales(
        documento=Documento(TipoDocumento(orm.tipo_documento), orm.nro_documento),
        nombre=orm.nombre,
        apellido=orm.apellido,
        fecha_nacimiento=orm.fecha_nacimiento,
        email=Email(orm.email) if orm.email else None,
        telefono=Telefono(orm.telefono) if orm.telefono else None,
        domicilio=orm.domicilio,
    )
    return Socio(
        id=orm.id,
        numero_socio=orm.numero_socio,
        datos=datos,
        sede_alta_id=orm.sede_alta_id,
        estado=EstadoSocio(orm.estado),
        causas=causas,
        motivo_administrativo=orm.motivo_administrativo,
        fecha_alta=orm.creado_en,
        fecha_baja=orm.fecha_baja,
        motivo_baja=orm.motivo_baja,
        creado_por=ref(orm.creado_por_id),
        actualizado_en=orm.actualizado_en,
        actualizado_por=ref(orm.actualizado_por_id),
        sede_alta_nombre=orm.sede_alta.nombre if orm.sede_alta else None,
        cuenta=(
            CuentaSocio(cuenta.id, cuenta.username, cuenta.activo) if cuenta is not None else None
        ),
    )


def _copiar_a_orm(socio: Socio, orm: SocioORM) -> None:
    datos = socio.datos
    orm.tipo_documento = datos.documento.tipo.value
    orm.nro_documento = datos.documento.numero
    orm.nombre = datos.nombre
    orm.apellido = datos.apellido
    orm.fecha_nacimiento = datos.fecha_nacimiento
    orm.email = datos.email.valor if datos.email else None
    orm.telefono = datos.telefono.valor if datos.telefono else None
    orm.domicilio = datos.domicilio
    orm.estado = socio.estado.value
    motivo = socio.motivo_inhabilitacion
    orm.motivo_inhabilitacion = motivo.value if motivo else None
    orm.inhabilitacion_administrativa = socio.inhabilitado_administrativamente
    orm.motivo_administrativo = socio.motivo_administrativo
    orm.fecha_baja = socio.fecha_baja
    orm.motivo_baja = socio.motivo_baja
    if socio.actualizado_en is not None:
        orm.actualizado_en = socio.actualizado_en
    orm.actualizado_por_id = socio.actualizado_por.id if socio.actualizado_por else None


class SqlAlchemySocioRepository:
    """Implementa ``SocioRepository`` con SQLAlchemy."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- lectura --------------------------------------------------------------------------

    def siguiente_numero(self) -> str:
        valor = self._sesion.scalar(SECUENCIA_NUMERO_SOCIO.next_value())
        assert valor is not None
        return formatear_numero_socio(int(valor))

    def obtener(self, socio_id: int) -> Socio | None:
        return self._uno(select(SocioORM).where(SocioORM.id == socio_id))

    def obtener_para_modificar(self, socio_id: int) -> Socio | None:
        consulta = (
            select(SocioORM)
            .where(SocioORM.id == socio_id)
            .with_for_update(of=SocioORM)
            .execution_options(populate_existing=True)
        )
        return self._uno(consulta)

    def buscar_por_documento(
        self, documento: Documento, excluir_id: int | None = None
    ) -> Socio | None:
        consulta = select(SocioORM).where(
            SocioORM.tipo_documento == documento.tipo.value,
            SocioORM.nro_documento == documento.numero,
        )
        if excluir_id is not None:
            consulta = consulta.where(SocioORM.id != excluir_id)
        return self._uno(consulta)

    def buscar_por_persona(
        self, nombre: str, apellido: str, fecha_nacimiento: date, excluir_id: int | None = None
    ) -> list[Socio]:
        nombre_sql = func.regexp_replace(func.btrim(sin_tildes(SocioORM.nombre)), r"\s+", " ", "g")
        apellido_sql = func.regexp_replace(
            func.btrim(sin_tildes(SocioORM.apellido)), r"\s+", " ", "g"
        )
        consulta = select(SocioORM).where(
            nombre_sql == nombre,
            apellido_sql == apellido,
            SocioORM.fecha_nacimiento == fecha_nacimiento,
        )
        if excluir_id is not None:
            consulta = consulta.where(SocioORM.id != excluir_id)
        return self._mapear(list(self._sesion.scalars(consulta.order_by(SocioORM.id))))

    def listar(self, filtro: FiltroSocios, page: int, size: int) -> tuple[list[Socio], int]:
        condiciones = self._condiciones(filtro)
        total = self._sesion.scalar(select(func.count(SocioORM.id)).where(*condiciones))
        filas = list(
            self._sesion.scalars(
                select(SocioORM)
                .where(*condiciones)
                .order_by(
                    sin_tildes(SocioORM.apellido).collate("C"),
                    sin_tildes(SocioORM.nombre).collate("C"),
                    SocioORM.id,
                )
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return self._mapear(filas), total or 0

    def situacion(self, socio_id: int) -> SituacionSocio:
        """Cuenta los préstamos en curso y vencidos (multas y reservas las suman sus módulos)."""
        por_estado = dict(
            self._sesion.execute(
                select(PrestamoORM.estado, func.count(PrestamoORM.id))
                .where(
                    PrestamoORM.socio_id == socio_id,
                    PrestamoORM.estado.in_(["SOLICITADO", "EN_ENVIO", "ACTIVO", "VENCIDO"]),
                )
                .group_by(PrestamoORM.estado)
            ).all()
        )
        vencidos = por_estado.pop("VENCIDO", 0)
        return SituacionSocio(
            prestamos_activos=sum(por_estado.values()), prestamos_vencidos=vencidos
        )

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, socio: Socio) -> None:
        orm = SocioORM(
            numero_socio=socio.numero_socio,
            sede_alta_id=socio.sede_alta_id,
            creado_por_id=socio.creado_por.id if socio.creado_por else None,
        )
        if socio.fecha_alta is not None:
            orm.creado_en = socio.fecha_alta
        _copiar_a_orm(socio, orm)
        self._persistir(lambda: self._sesion.add(orm))
        socio.id = orm.id

    def guardar(self, socio: Socio) -> None:
        assert socio.id is not None
        orm = self._sesion.get(SocioORM, socio.id)
        assert orm is not None
        _copiar_a_orm(socio, orm)
        self._persistir(lambda: None)

    # --- internos -------------------------------------------------------------------------

    def _persistir(self, preparar: Any) -> None:
        """Escribe dentro de un savepoint y traduce el documento repetido."""
        try:
            with self._sesion.begin_nested():
                preparar()
                self._sesion.flush()
        except IntegrityError as error:
            restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if restriccion != "uq_socio_tipo_documento_nro_documento":
                raise
            raise DuplicadoError(
                "Ya existe un socio con ese documento.",
                [{"campo": "nro_documento", "problema": "duplicado"}],
            ) from error

    def _uno(self, consulta: Any) -> Socio | None:
        orm = self._sesion.scalars(consulta).first()
        return self._mapear([orm])[0] if orm is not None else None

    def _mapear(self, filas: list[SocioORM]) -> list[Socio]:
        if not filas:
            return []
        ids: set[int] = set()
        for fila in filas:
            ids.update(i for i in (fila.creado_por_id, fila.actualizado_por_id) if i is not None)
        nombres = nombres_de_usuarios(self._sesion, ids)
        cuentas = {
            c.socio_id: c
            for c in self._sesion.scalars(
                select(UsuarioORM).where(UsuarioORM.socio_id.in_([f.id for f in filas]))
            )
        }
        return [_a_dominio(f, nombres, cuentas.get(f.id)) for f in filas]

    @staticmethod
    def _condiciones(filtro: FiltroSocios) -> list[ColumnElement[bool]]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.estado is not None:
            condiciones.append(SocioORM.estado == filtro.estado.value)
        if filtro.documento:
            condiciones.append(SocioORM.nro_documento == filtro.documento)
        if filtro.texto:
            persona = sin_tildes(SocioORM.nombre + " " + SocioORM.apellido)
            persona_inversa = sin_tildes(SocioORM.apellido + " " + SocioORM.nombre)
            condiciones.append(
                persona.contains(filtro.texto, autoescape=True)
                | persona_inversa.contains(filtro.texto, autoescape=True)
                | SocioORM.numero_socio.contains(filtro.texto, autoescape=True)
                | SocioORM.nro_documento.contains(
                    filtro.texto.replace(".", "").replace(" ", "").upper(), autoescape=True
                )
            )
        return condiciones
