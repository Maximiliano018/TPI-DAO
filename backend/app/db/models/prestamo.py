"""Tablas de préstamos, remitos, incidencias y parámetros de negocio."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.catalogo import EjemplarORM
    from app.db.models.sede import SedeORM
    from app.db.models.socio import SocioORM

SECUENCIA_PRESTAMO = Sequence("prestamo_numero_seq", metadata=Base.metadata)
SECUENCIA_REMITO = Sequence("remito_numero_seq", metadata=Base.metadata)

ESTADOS_PRESTAMO_ABIERTOS = "'SOLICITADO','EN_ENVIO','ACTIVO','VENCIDO'"
ESTADOS_REMITO_ABIERTOS = "'GENERADO','EMPAQUETADO','DESPACHADO','EN_TRANSITO'"


class ParametroORM(Base):
    """Parámetro de negocio editable por el administrador (clave y valor en texto)."""

    __tablename__ = "parametro"

    clave: Mapped[str] = mapped_column(String(40), primary_key=True)
    valor: Mapped[str] = mapped_column(String(40), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)


class PrestamoORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "prestamo"
    __table_args__ = (
        CheckConstraint("tipo IN ('LOCAL','INTERBIBLIOTECARIO')", name="tipo_valido"),
        CheckConstraint(
            "estado IN ('SOLICITADO','EN_ENVIO','ACTIVO','VENCIDO','DEVUELTO','CANCELADO')",
            name="estado_valido",
        ),
        CheckConstraint(
            "(tipo = 'LOCAL' AND sede_origen_id = sede_destino_id)"
            " OR (tipo = 'INTERBIBLIOTECARIO' AND sede_origen_id <> sede_destino_id)",
            name="sedes_segun_tipo",
        ),
        CheckConstraint("renovaciones >= 0", name="renovaciones_no_negativas"),
        CheckConstraint(
            "(estado IN ('ACTIVO','VENCIDO','DEVUELTO')) "
            "= (fecha_inicio IS NOT NULL AND fecha_vencimiento IS NOT NULL)",
            name="fechas_segun_estado",
        ),
        CheckConstraint(
            "(estado = 'DEVUELTO') = (fecha_devolucion IS NOT NULL)",
            name="devolucion_con_fecha",
        ),
        Index(
            "uq_prestamo_abierto_por_ejemplar",
            "ejemplar_id",
            unique=True,
            postgresql_where=text(f"estado IN ({ESTADOS_PRESTAMO_ABIERTOS})"),
        ),
        Index("ix_prestamo_socio_id_estado", "socio_id", "estado"),
        Index("ix_prestamo_estado_fecha_vencimiento", "estado", "fecha_vencimiento"),
        Index("ix_prestamo_tipo_fecha_solicitud", "tipo", "fecha_solicitud"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socio.id"), nullable=False)
    ejemplar_id: Mapped[int] = mapped_column(ForeignKey("ejemplar.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    sede_origen_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    sede_destino_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    fecha_devolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    renovaciones: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    fecha_limite_retiro: Mapped[date | None] = mapped_column(Date)
    # NULL cuando el préstamo lo generó el sistema al asignar una reserva entre sedes.
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    socio: Mapped["SocioORM"] = relationship(lazy="joined")
    ejemplar: Mapped["EjemplarORM"] = relationship(lazy="joined")
    sede_origen: Mapped["SedeORM"] = relationship(foreign_keys=[sede_origen_id], lazy="joined")
    sede_destino: Mapped["SedeORM"] = relationship(foreign_keys=[sede_destino_id], lazy="joined")


class RemitoORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "remito"
    __table_args__ = (
        CheckConstraint("sede_origen_id <> sede_destino_id", name="sedes_distintas"),
        CheckConstraint("motivo IN ('ENVIO','RETORNO','TRASLADO')", name="motivo_valido"),
        CheckConstraint(
            "estado IN ('GENERADO','EMPAQUETADO','DESPACHADO','EN_TRANSITO','RECIBIDO',"
            "'EXTRAVIADO','DANADO','DESTRUIDO','ANULADO')",
            name="estado_valido",
        ),
        Index(
            "ix_remito_estado_sede_origen_id_sede_destino_id",
            "estado",
            "sede_origen_id",
            "sede_destino_id",
        ),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    sede_origen_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    sede_destino_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    motivo: Mapped[str] = mapped_column(String(15), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_despacho: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    sede_origen: Mapped["SedeORM"] = relationship(foreign_keys=[sede_origen_id], lazy="joined")
    sede_destino: Mapped["SedeORM"] = relationship(foreign_keys=[sede_destino_id], lazy="joined")
    lineas: Mapped[list["DetalleRemitoORM"]] = relationship(
        back_populates="remito", order_by="DetalleRemitoORM.id", lazy="selectin"
    )


class DetalleRemitoORM(Base):
    __tablename__ = "detalle_remito"
    __table_args__ = (UniqueConstraint("remito_id", "ejemplar_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    remito_id: Mapped[int] = mapped_column(ForeignKey("remito.id"), nullable=False)
    ejemplar_id: Mapped[int] = mapped_column(ForeignKey("ejemplar.id"), nullable=False)
    prestamo_id: Mapped[int | None] = mapped_column(ForeignKey("prestamo.id"))
    estado_fisico_salida: Mapped[str] = mapped_column(String(10), nullable=False)
    estado_fisico_llegada: Mapped[str | None] = mapped_column(String(10))
    resultado: Mapped[str | None] = mapped_column(String(10))
    observacion: Mapped[str | None] = mapped_column(Text)

    remito: Mapped[RemitoORM] = relationship(back_populates="lineas")
    ejemplar: Mapped["EjemplarORM"] = relationship(lazy="joined")


class _Movimiento:
    """Columnas comunes de los historiales de solo inserción."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(15))
    estado_nuevo: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    observacion: Mapped[str | None] = mapped_column(Text)


class MovimientoPrestamoORM(_Movimiento, Base):
    __tablename__ = "movimiento_prestamo"
    __table_args__ = (
        Index("ix_movimiento_prestamo_prestamo_id_fecha_hora", "prestamo_id", "fecha_hora"),
    )

    prestamo_id: Mapped[int] = mapped_column(ForeignKey("prestamo.id"), nullable=False)


class MovimientoRemitoORM(_Movimiento, Base):
    __tablename__ = "movimiento_remito"
    __table_args__ = (
        Index("ix_movimiento_remito_remito_id_fecha_hora", "remito_id", "fecha_hora"),
    )

    remito_id: Mapped[int] = mapped_column(ForeignKey("remito.id"), nullable=False)


class IncidenciaORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "incidencia"
    __table_args__ = (
        CheckConstraint("tipo IN ('EXTRAVIO','DANIO','DESTRUCCION')", name="tipo_valido"),
        CheckConstraint("origen IN ('DEVOLUCION','REMITO')", name="origen_valido"),
    )

    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    origen: Mapped[str] = mapped_column(String(15), nullable=False)
    ejemplar_id: Mapped[int] = mapped_column(ForeignKey("ejemplar.id"), nullable=False)
    socio_id: Mapped[int | None] = mapped_column(ForeignKey("socio.id"))
    prestamo_id: Mapped[int | None] = mapped_column(ForeignKey("prestamo.id"))
    remito_id: Mapped[int | None] = mapped_column(ForeignKey("remito.id"))
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


SECUENCIA_RESERVA = Sequence("reserva_numero_seq", metadata=Base.metadata)


class ReservaORM(ConAuditoriaDeTiempo, Base):
    """Reserva de un libro (cola FIFO por ``fecha_reserva``)."""

    __tablename__ = "reserva"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE','DISPONIBLE_PARA_RETIRO','CUMPLIDA','CANCELADA','VENCIDA')",
            name="estado_valido",
        ),
        CheckConstraint(
            "estado <> 'DISPONIBLE_PARA_RETIRO' OR "
            "(ejemplar_id IS NOT NULL AND vencimiento_retiro IS NOT NULL)",
            name="disponible_con_ejemplar",
        ),
        Index(
            "uq_reserva_activa",
            "socio_id",
            "libro_id",
            unique=True,
            postgresql_where=text("estado IN ('PENDIENTE','DISPONIBLE_PARA_RETIRO')"),
        ),
        Index("ix_reserva_libro_id_estado_fecha_reserva", "libro_id", "estado", "fecha_reserva"),
    )

    numero: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socio.id"), nullable=False)
    libro_id: Mapped[int] = mapped_column(ForeignKey("libro.id"), nullable=False)
    sede_retiro_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    ejemplar_id: Mapped[int | None] = mapped_column(ForeignKey("ejemplar.id"))
    prestamo_id: Mapped[int | None] = mapped_column(ForeignKey("prestamo.id"))
    estado: Mapped[str] = mapped_column(String(25), nullable=False)
    fecha_reserva: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vencimiento_retiro: Mapped[date | None] = mapped_column(Date)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registrada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    socio: Mapped["SocioORM"] = relationship(lazy="joined")
    sede_retiro: Mapped["SedeORM"] = relationship(lazy="joined")
    ejemplar: Mapped["EjemplarORM | None"] = relationship(lazy="joined")
