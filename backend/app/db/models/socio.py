"""Tabla de socios de la red."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.sede import SedeORM

SECUENCIA_NUMERO_SOCIO = Sequence("socio_numero_seq", metadata=Base.metadata)
_CAUSAS = "(inhabilitacion_administrativa OR causa_prestamo_vencido OR causa_multa_impaga)"


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
            f"(motivo_inhabilitacion IS NOT NULL) = {_CAUSAS}", name="motivo_con_causas"
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
            "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL "
            "AND tipo_baja IS NOT NULL) OR (estado <> 'BAJA' AND fecha_baja IS NULL "
            "AND motivo_baja IS NULL AND tipo_baja IS NULL)",
            name="baja_con_datos",
        ),
        CheckConstraint(
            "tipo_baja IS NULL OR tipo_baja IN ('FALLECIMIENTO','ADMINISTRATIVA','A_PEDIDO')",
            name="tipo_baja_valido",
        ),
        CheckConstraint(
            "(reactivacion_solicitada_en IS NULL "
            "OR (estado = 'BAJA' AND tipo_baja <> 'FALLECIMIENTO')) "
            "AND (mensaje_solicitud IS NULL OR reactivacion_solicitada_en IS NOT NULL)",
            name="solicitud_coherente",
        ),
        # En baja se conserva la inhabilitación administrativa, nunca las causas automáticas.
        CheckConstraint(
            f"CASE estado WHEN 'HABILITADO' THEN NOT {_CAUSAS} "
            f"WHEN 'INHABILITADO' THEN {_CAUSAS} "
            "ELSE NOT (causa_prestamo_vencido OR causa_multa_impaga) END",
            name="causas_coherentes",
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
    causa_prestamo_vencido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    causa_multa_impaga: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    tipo_baja: Mapped[str | None] = mapped_column(String(15))
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_baja: Mapped[str | None] = mapped_column(String(300))
    reactivacion_solicitada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mensaje_solicitud: Mapped[str | None] = mapped_column(String(300))
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    sede_alta: Mapped["SedeORM"] = relationship(foreign_keys=[sede_alta_id], lazy="joined")


class HistorialSocioORM(ConAuditoriaDeTiempo, Base):
    """Historial de solo inserción del socio (un disparador impide UPDATE y DELETE).

    ``usuario_id`` es nulo cuando el cambio lo hizo el sistema (inhabilitación automática).
    """

    __tablename__ = "historial_socio"
    __table_args__ = (
        CheckConstraint(
            "tipo_evento IN ('ALTA','MODIFICACION','INHABILITACION','REHABILITACION',"
            "'CAMBIO_AUTOMATICO','BAJA','SOLICITUD_REACTIVACION','SOLICITUD_RECHAZADA',"
            "'REACTIVACION','CUENTA_CREADA')",
            name="tipo_evento_valido",
        ),
        Index("ix_historial_socio_socio_id_fecha_hora", "socio_id", text("fecha_hora DESC")),
    )

    socio_id: Mapped[int] = mapped_column(ForeignKey("socio.id"), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(25), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    estado_anterior: Mapped[str | None] = mapped_column(String(15))
    estado_nuevo: Mapped[str | None] = mapped_column(String(15))
    motivo: Mapped[str | None] = mapped_column(String(300))
    origen: Mapped[str | None] = mapped_column(String(200))
    cambios: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
