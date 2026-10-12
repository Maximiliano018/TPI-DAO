"""Esquema de la base de datos (SQLAlchemy Core).

Las tablas se definen sin clases ORM: más adelante se mapean de forma imperativa sobre
las entidades del dominio (ARCHITECTURE.md §5.4). Cada restricción corresponde al
diccionario de datos (§5.1) y a los invariantes (§5.2).
"""

from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Time,
    UniqueConstraint,
    func,
    text,
    true,
)

from biblioteca.domain.enums import (
    ESTADOS_PRESTAMO_ABIERTOS,
    ESTADOS_REMITO_NO_FINALES,
    ESTADOS_RESERVA_ABIERTOS,
    CanalNotificacion,
    CondicionFisica,
    EstadoEjemplar,
    EstadoMulta,
    EstadoPrestamo,
    EstadoRemito,
    EstadoReserva,
    MotivoBaja,
    MotivoCancelacion,
    ResultadoRevision,
    Rol,
    Sentido,
    TipoNotificacion,
    TipoParametro,
)
from biblioteca.infrastructure.db.tipos import FechaHoraUTC

# Nombres de restricciones estables: Alembic los necesita en modo batch (SQLite).
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def _lista(valores: tuple[StrEnum, ...] | type[StrEnum]) -> str:
    return ", ".join(f"'{v.value}'" for v in valores)


def _check_enum(columna: str, enum: type[StrEnum]) -> CheckConstraint:
    """Restringe una columna de texto a los valores de la enumeración (NULL se admite)."""
    return CheckConstraint(f"{columna} IN ({_lista(enum)})", name=f"{columna}_valido")


def _fk(tabla: str) -> ForeignKey:
    """FK al id de otra tabla. Sin borrados en cascada: las bajas son lógicas."""
    return ForeignKey(f"{tabla}.id", ondelete="RESTRICT")


def _id() -> Column[int]:
    return Column("id", Integer, primary_key=True)


def _marcas_de_tiempo() -> list[Column[Any]]:
    return [
        Column(
            "creado_en", FechaHoraUTC(), nullable=False, server_default=func.current_timestamp()
        ),
        Column(
            "actualizado_en",
            FechaHoraUTC(),
            nullable=False,
            server_default=func.current_timestamp(),
            onupdate=func.current_timestamp(),
        ),
    ]


# --------------------------------------------------------------------------- Organización

sede = Table(
    "sede",
    metadata,
    _id(),
    Column("codigo", String(5), nullable=False, unique=True),
    Column("nombre", String(100), nullable=False, unique=True),
    Column("direccion", String(200), nullable=False),
    Column("localidad", String(100), nullable=False),
    Column("telefono", String(30)),
    Column("email", String(120)),
    Column("activa", Boolean, nullable=False, server_default=true()),
    Column("fecha_baja", FechaHoraUTC()),
    *_marcas_de_tiempo(),
    CheckConstraint("length(codigo) BETWEEN 2 AND 5", name="codigo_largo"),
    CheckConstraint("activa = (fecha_baja IS NULL)", name="baja_con_fecha"),
)

horario_sede = Table(
    "horario_sede",
    metadata,
    _id(),
    Column("sede_id", ForeignKey("sede.id", ondelete="CASCADE"), nullable=False),
    Column("dia_semana", Integer, nullable=False),
    Column("hora_apertura", Time, nullable=False),
    Column("hora_cierre", Time, nullable=False),
    *_marcas_de_tiempo(),
    CheckConstraint("dia_semana BETWEEN 1 AND 7", name="dia_semana_valido"),
    CheckConstraint("hora_apertura < hora_cierre", name="franja_valida"),
    UniqueConstraint("sede_id", "dia_semana", "hora_apertura"),
)

usuario = Table(
    "usuario",
    metadata,
    _id(),
    Column("username", String(50), nullable=False, unique=True),
    Column("nombre_completo", String(150), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("rol", String(20), nullable=False),
    Column("sede_id", _fk("sede")),
    Column("activo", Boolean, nullable=False, server_default=true()),
    *_marcas_de_tiempo(),
    _check_enum("rol", Rol),
    CheckConstraint(f"(rol = '{Rol.ADMIN}') = (sede_id IS NULL)", name="admin_sin_sede"),
)

parametro = Table(
    "parametro",
    metadata,
    Column("clave", String(50), primary_key=True),
    Column("valor", String(100), nullable=False),
    Column("tipo", String(10), nullable=False),
    Column("descripcion", String(255)),
    Column("actualizado_por", _fk("usuario")),
    *_marcas_de_tiempo(),
    _check_enum("tipo", TipoParametro),
)

secuencia = Table(
    "secuencia",
    metadata,
    Column("nombre", String(50), primary_key=True),
    Column("ultimo_valor", Integer, nullable=False, server_default=text("0")),
    CheckConstraint("ultimo_valor >= 0", name="ultimo_valor_no_negativo"),
)

# ------------------------------------------------------------------------------ Catálogo

categoria = Table(
    "categoria",
    metadata,
    _id(),
    Column("nombre", String(100), nullable=False, unique=True),
    *_marcas_de_tiempo(),
)

autor = Table(
    "autor",
    metadata,
    _id(),
    Column("nombre", String(150), nullable=False),
    Column("nombre_normalizado", String(150), nullable=False, unique=True),
    *_marcas_de_tiempo(),
)

libro = Table(
    "libro",
    metadata,
    _id(),
    Column("isbn", String(13), nullable=False, unique=True),
    Column("titulo", String(255), nullable=False),
    Column("editorial", String(150)),
    Column("anio_publicacion", Integer),
    Column("categoria_id", _fk("categoria")),
    *_marcas_de_tiempo(),
    CheckConstraint("length(isbn) = 13", name="isbn_13_digitos"),
)

libro_autor = Table(
    "libro_autor",
    metadata,
    Column("libro_id", ForeignKey("libro.id", ondelete="CASCADE"), primary_key=True),
    Column("autor_id", ForeignKey("autor.id", ondelete="RESTRICT"), primary_key=True),
    Column("orden", Integer, nullable=False),
    CheckConstraint("orden >= 1", name="orden_positivo"),
    UniqueConstraint("libro_id", "orden"),
)

ejemplar = Table(
    "ejemplar",
    metadata,
    _id(),
    Column("codigo_inventario", String(20), nullable=False, unique=True),
    Column("libro_id", _fk("libro"), nullable=False),
    Column("sede_id", _fk("sede"), nullable=False),
    Column("estado", String(20), nullable=False, server_default=EstadoEjemplar.DISPONIBLE.value),
    Column(
        "condicion_fisica", String(10), nullable=False, server_default=CondicionFisica.BUENA.value
    ),
    Column("prestable", Boolean, nullable=False, server_default=true()),
    Column("fecha_alta", Date, nullable=False),
    Column("fecha_baja", Date),
    Column("motivo_baja", String(15)),
    *_marcas_de_tiempo(),
    _check_enum("estado", EstadoEjemplar),
    _check_enum("condicion_fisica", CondicionFisica),
    _check_enum("motivo_baja", MotivoBaja),
    CheckConstraint(
        f"(estado = '{EstadoEjemplar.BAJA}') = (motivo_baja IS NOT NULL)", name="baja_con_motivo"
    ),
    CheckConstraint(
        f"(estado = '{EstadoEjemplar.BAJA}') = (fecha_baja IS NOT NULL)", name="baja_con_fecha"
    ),
)
Index("ix_ejemplar_libro_sede_estado", ejemplar.c.libro_id, ejemplar.c.sede_id, ejemplar.c.estado)

# -------------------------------------------------------------------------------- Socios

socio = Table(
    "socio",
    metadata,
    _id(),
    Column("numero_socio", Integer, nullable=False, unique=True),
    Column("dni", String(15), nullable=False, unique=True),
    Column("nombre", String(100), nullable=False),
    Column("apellido", String(100), nullable=False),
    Column("email", String(120)),
    Column("telefono", String(30)),
    Column("direccion", String(200)),
    Column("fecha_alta", Date, nullable=False),
    Column("habilitado", Boolean, nullable=False, server_default=true()),
    Column("motivo_inhabilitacion", String(255)),
    Column("fecha_inhabilitacion", FechaHoraUTC()),
    Column("activo", Boolean, nullable=False, server_default=true()),
    *_marcas_de_tiempo(),
    CheckConstraint(
        "habilitado = (motivo_inhabilitacion IS NULL)", name="inhabilitacion_con_motivo"
    ),
)

# --------------------------------------------------------------------------- Circulación

_PRESTAMO_ABIERTO = f"estado IN ({_lista(ESTADOS_PRESTAMO_ABIERTOS)})"

prestamo = Table(
    "prestamo",
    metadata,
    _id(),
    Column("socio_id", _fk("socio"), nullable=False),
    Column("ejemplar_id", _fk("ejemplar"), nullable=False),
    Column("sede_origen_id", _fk("sede"), nullable=False),
    Column("sede_destino_id", _fk("sede"), nullable=False),
    Column("estado", String(20), nullable=False),
    Column("fecha_solicitud", FechaHoraUTC(), nullable=False),
    Column("fecha_limite_retiro", Date),
    Column("fecha_inicio", Date),
    Column("fecha_vencimiento", Date),
    Column("fecha_cierre", FechaHoraUTC()),
    Column("motivo_cancelacion", String(20)),
    Column("registrado_por", _fk("usuario"), nullable=False),
    *_marcas_de_tiempo(),
    _check_enum("estado", EstadoPrestamo),
    _check_enum("motivo_cancelacion", MotivoCancelacion),
    CheckConstraint(
        f"estado NOT IN ('{EstadoPrestamo.ACTIVO}', '{EstadoPrestamo.DEVUELTO}') "
        "OR (fecha_inicio IS NOT NULL AND fecha_vencimiento IS NOT NULL)",
        name="entregado_con_fechas",
    ),
    CheckConstraint(
        "fecha_vencimiento IS NULL OR fecha_vencimiento >= fecha_inicio",
        name="vencimiento_posterior_al_inicio",
    ),
    CheckConstraint(
        f"estado <> '{EstadoPrestamo.LISTO_PARA_RETIRO}' OR fecha_limite_retiro IS NOT NULL",
        name="listo_con_limite_retiro",
    ),
    CheckConstraint(
        f"estado NOT IN ('{EstadoPrestamo.EN_ENVIO}', '{EstadoPrestamo.LISTO_PARA_RETIRO}') "
        "OR sede_origen_id <> sede_destino_id",
        name="envio_entre_sedes_distintas",
    ),
    CheckConstraint(
        f"(estado = '{EstadoPrestamo.CANCELADO}') = (motivo_cancelacion IS NOT NULL)",
        name="cancelado_con_motivo",
    ),
    CheckConstraint(
        f"(estado IN ('{EstadoPrestamo.DEVUELTO}', '{EstadoPrestamo.CANCELADO}')) "
        "= (fecha_cierre IS NOT NULL)",
        name="cerrado_con_fecha",
    ),
)
Index(
    "uq_prestamo_ejemplar_abierto",
    prestamo.c.ejemplar_id,
    unique=True,
    sqlite_where=text(_PRESTAMO_ABIERTO),
    postgresql_where=text(_PRESTAMO_ABIERTO),
)
Index("ix_prestamo_socio_estado", prestamo.c.socio_id, prestamo.c.estado)
Index("ix_prestamo_estado_vencimiento", prestamo.c.estado, prestamo.c.fecha_vencimiento)

devolucion = Table(
    "devolucion",
    metadata,
    _id(),
    Column("prestamo_id", _fk("prestamo"), nullable=False, unique=True),
    Column("fecha_hora", FechaHoraUTC(), nullable=False),
    Column("condicion_fisica", String(10), nullable=False),
    Column("observacion", String(500)),
    Column("registrado_por", _fk("usuario"), nullable=False),
    *_marcas_de_tiempo(),
    _check_enum("condicion_fisica", CondicionFisica),
)

multa = Table(
    "multa",
    metadata,
    _id(),
    Column("prestamo_id", _fk("prestamo"), nullable=False, unique=True),
    Column("dias_atraso", Integer, nullable=False),
    Column("monto_por_dia", Integer, nullable=False),
    Column("monto", Integer, nullable=False),
    Column("estado", String(10), nullable=False, server_default=EstadoMulta.PENDIENTE.value),
    Column("fecha_generacion", FechaHoraUTC(), nullable=False),
    Column("fecha_saldada", FechaHoraUTC()),
    Column("saldada_por", _fk("usuario")),
    *_marcas_de_tiempo(),
    _check_enum("estado", EstadoMulta),
    CheckConstraint("dias_atraso > 0", name="dias_atraso_positivo"),
    CheckConstraint("monto_por_dia > 0", name="monto_por_dia_positivo"),
    CheckConstraint("monto > 0", name="monto_positivo"),
    CheckConstraint(
        f"(estado = '{EstadoMulta.SALDADA}') = (fecha_saldada IS NOT NULL)",
        name="saldada_con_fecha",
    ),
    CheckConstraint(
        f"(estado = '{EstadoMulta.SALDADA}') = (saldada_por IS NOT NULL)",
        name="saldada_con_usuario",
    ),
)
Index("ix_multa_estado", multa.c.estado)

_RESERVA_ABIERTA = f"estado IN ({_lista(ESTADOS_RESERVA_ABIERTOS)})"
_RESERVA_ASIGNADA = f"estado = '{EstadoReserva.ASIGNADA}'"

reserva = Table(
    "reserva",
    metadata,
    _id(),
    Column("socio_id", _fk("socio"), nullable=False),
    Column("libro_id", _fk("libro"), nullable=False),
    Column("sede_id", _fk("sede"), nullable=False),
    Column("estado", String(10), nullable=False, server_default=EstadoReserva.PENDIENTE.value),
    Column("fecha_solicitud", FechaHoraUTC(), nullable=False),
    Column("ejemplar_asignado_id", _fk("ejemplar")),
    Column("fecha_asignacion", FechaHoraUTC()),
    Column("fecha_limite", Date),
    Column("prestamo_id", _fk("prestamo"), unique=True),
    Column("fecha_cierre", FechaHoraUTC()),
    Column("registrado_por", _fk("usuario"), nullable=False),
    *_marcas_de_tiempo(),
    _check_enum("estado", EstadoReserva),
    CheckConstraint(
        f"estado NOT IN ('{EstadoReserva.ASIGNADA}', '{EstadoReserva.CUMPLIDA}') "
        "OR (ejemplar_asignado_id IS NOT NULL AND fecha_asignacion IS NOT NULL)",
        name="asignada_con_ejemplar",
    ),
    CheckConstraint(
        f"estado <> '{EstadoReserva.ASIGNADA}' OR fecha_limite IS NOT NULL",
        name="asignada_con_limite",
    ),
    CheckConstraint(
        f"(estado = '{EstadoReserva.CUMPLIDA}') = (prestamo_id IS NOT NULL)",
        name="cumplida_con_prestamo",
    ),
    CheckConstraint(
        f"(estado IN ('{EstadoReserva.CUMPLIDA}', '{EstadoReserva.CANCELADA}', "
        f"'{EstadoReserva.VENCIDA}')) = (fecha_cierre IS NOT NULL)",
        name="cerrada_con_fecha",
    ),
)
Index(
    "uq_reserva_ejemplar_asignado",
    reserva.c.ejemplar_asignado_id,
    unique=True,
    sqlite_where=text(_RESERVA_ASIGNADA),
    postgresql_where=text(_RESERVA_ASIGNADA),
)
Index(
    "uq_reserva_socio_libro_abierta",
    reserva.c.socio_id,
    reserva.c.libro_id,
    unique=True,
    sqlite_where=text(_RESERVA_ABIERTA),
    postgresql_where=text(_RESERVA_ABIERTA),
)
Index(
    "ix_reserva_cola",
    reserva.c.libro_id,
    reserva.c.sede_id,
    reserva.c.estado,
    reserva.c.fecha_solicitud,
)

# ----------------------------------------------------------------------------- Logística

_REMITO_NO_FINAL = f"estado IN ({_lista(ESTADOS_REMITO_NO_FINALES)})"
_REMITO_VIGENTE = f"estado <> '{EstadoRemito.CANCELADO}'"
_REMITO_DESPACHADO = (
    f"estado IN ('{EstadoRemito.EN_TRANSITO}', '{EstadoRemito.RECIBIDO}', "
    f"'{EstadoRemito.EXTRAVIADO}')"
)

remito = Table(
    "remito",
    metadata,
    _id(),
    Column("numero", String(20), nullable=False, unique=True),
    Column("ejemplar_id", _fk("ejemplar"), nullable=False),
    Column("prestamo_id", _fk("prestamo")),
    Column("sentido", String(10), nullable=False),
    Column("sede_origen_id", _fk("sede"), nullable=False),
    Column("sede_destino_id", _fk("sede"), nullable=False),
    Column("estado", String(15), nullable=False, server_default=EstadoRemito.GENERADO.value),
    Column("fecha_generacion", FechaHoraUTC(), nullable=False),
    Column("fecha_despacho", FechaHoraUTC()),
    Column("fecha_recepcion", FechaHoraUTC()),
    Column("resultado_revision", String(10)),
    Column("observacion_revision", String(500)),
    *_marcas_de_tiempo(),
    _check_enum("sentido", Sentido),
    _check_enum("estado", EstadoRemito),
    _check_enum("resultado_revision", ResultadoRevision),
    CheckConstraint("sede_origen_id <> sede_destino_id", name="sedes_distintas"),
    CheckConstraint(
        f"({_REMITO_DESPACHADO}) = (fecha_despacho IS NOT NULL)", name="despachado_con_fecha"
    ),
    CheckConstraint(
        f"(estado = '{EstadoRemito.RECIBIDO}') = (fecha_recepcion IS NOT NULL)",
        name="recibido_con_fecha",
    ),
    CheckConstraint(
        f"(estado = '{EstadoRemito.RECIBIDO}') = (resultado_revision IS NOT NULL)",
        name="recibido_con_revision",
    ),
)
Index(
    "uq_remito_ejemplar_no_final",
    remito.c.ejemplar_id,
    unique=True,
    sqlite_where=text(_REMITO_NO_FINAL),
    postgresql_where=text(_REMITO_NO_FINAL),
)
Index(
    "uq_remito_prestamo_sentido_vigente",
    remito.c.prestamo_id,
    remito.c.sentido,
    unique=True,
    sqlite_where=text(_REMITO_VIGENTE),
    postgresql_where=text(_REMITO_VIGENTE),
)
Index("ix_remito_estado_despacho", remito.c.estado, remito.c.fecha_despacho)
Index("ix_remito_origen_destino", remito.c.sede_origen_id, remito.c.sede_destino_id)

movimiento_remito = Table(
    "movimiento_remito",
    metadata,
    _id(),
    Column("remito_id", _fk("remito"), nullable=False),
    Column("estado_anterior", String(15)),
    Column("estado_nuevo", String(15), nullable=False),
    Column("fecha_hora", FechaHoraUTC(), nullable=False),
    Column("usuario_id", _fk("usuario"), nullable=False),
    Column("observacion", String(500)),
    CheckConstraint(f"estado_anterior IN ({_lista(EstadoRemito)})", name="estado_anterior_valido"),
    CheckConstraint(f"estado_nuevo IN ({_lista(EstadoRemito)})", name="estado_nuevo_valido"),
)
Index(
    "ix_movimiento_remito_remito_fecha",
    movimiento_remito.c.remito_id,
    movimiento_remito.c.fecha_hora,
)

# -------------------------------------------------------------------------- Notificaciones

_AVISO_VENCIMIENTO = (
    f"tipo IN ('{TipoNotificacion.VENCIMIENTO_PROXIMO}', '{TipoNotificacion.PRESTAMO_VENCIDO}')"
)

notificacion = Table(
    "notificacion",
    metadata,
    _id(),
    Column("socio_id", _fk("socio"), nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("prestamo_id", _fk("prestamo")),
    Column("reserva_id", _fk("reserva")),
    Column(
        "canal", String(20), nullable=False, server_default=CanalNotificacion.EMAIL_SIMULADO.value
    ),
    Column("mensaje", String(500), nullable=False),
    Column("fecha_hora", FechaHoraUTC(), nullable=False),
    _check_enum("tipo", TipoNotificacion),
    _check_enum("canal", CanalNotificacion),
    CheckConstraint(
        f"tipo = '{TipoNotificacion.RESERVA_ASIGNADA}' OR prestamo_id IS NOT NULL",
        name="aviso_de_prestamo_con_prestamo",
    ),
    CheckConstraint(
        f"tipo <> '{TipoNotificacion.RESERVA_ASIGNADA}' OR reserva_id IS NOT NULL",
        name="aviso_de_reserva_con_reserva",
    ),
)
Index(
    "uq_notificacion_aviso_vencimiento",
    notificacion.c.prestamo_id,
    notificacion.c.tipo,
    unique=True,
    sqlite_where=text(_AVISO_VENCIMIENTO),
    postgresql_where=text(_AVISO_VENCIMIENTO),
)
