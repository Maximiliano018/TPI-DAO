"""Tabla de socios de la red."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Sequence,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.sede import SedeORM

SECUENCIA_NUMERO_SOCIO = Sequence("socio_numero_seq", metadata=Base.metadata)


class SocioORM(ConAuditoriaDeTiempo, Base):
    """Socio. La baja es lógica: ``estado = 'BAJA'`` con fecha y motivo."""

    __tablename__ = "socio"
    __table_args__ = (
        UniqueConstraint("tipo_documento", "nro_documento"),
        CheckConstraint("estado IN ('HABILITADO','INHABILITADO','BAJA')", name="estado_valido"),
        CheckConstraint(
            "tipo_documento IN ('DNI','LE','LC','PASAPORTE')", name="tipo_documento_valido"
        ),
        CheckConstraint(
            "motivo_inhabilitacion IS NULL OR motivo_inhabilitacion IN "
            "('ADMINISTRATIVA','PRESTAMO_VENCIDO','MULTA_IMPAGA')",
            name="motivo_valido",
        ),
        CheckConstraint(
            "(estado = 'INHABILITADO') = (motivo_inhabilitacion IS NOT NULL)",
            name="inhabilitado_con_motivo",
        ),
        CheckConstraint(
            "inhabilitacion_administrativa = (motivo_administrativo IS NOT NULL)",
            name="administrativa_con_motivo",
        ),
        CheckConstraint(
            "NOT inhabilitacion_administrativa OR motivo_inhabilitacion = 'ADMINISTRATIVA'",
            name="administrativa_prioritaria",
        ),
        CheckConstraint(
            "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL)"
            " OR (estado <> 'BAJA' AND fecha_baja IS NULL AND motivo_baja IS NULL)",
            name="baja_con_datos",
        ),
        Index("ix_socio_apellido_nombre", "apellido", "nombre"),
    )

    numero_socio: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    tipo_documento: Mapped[str] = mapped_column(String(10), nullable=False)
    nro_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    domicilio: Mapped[str | None] = mapped_column(String(200))
    sede_alta_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="HABILITADO")
    motivo_inhabilitacion: Mapped[str | None] = mapped_column(String(30))
    inhabilitacion_administrativa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    motivo_administrativo: Mapped[str | None] = mapped_column(String(300))
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_baja: Mapped[str | None] = mapped_column(String(300))
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    sede_alta: Mapped["SedeORM"] = relationship(foreign_keys=[sede_alta_id], lazy="joined")
