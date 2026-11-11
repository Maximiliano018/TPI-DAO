"""Sedes, horarios, excepciones de horario e historial (auditoría)."""

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo
from app.db.models.geografia import LocalidadORM


class SedeORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "sede"
    __table_args__ = (
        CheckConstraint("codigo ~ '^[A-Z0-9_]{3,15}$'", name="codigo_formato"),
        CheckConstraint("telefono ~ '^\\+[1-9][0-9]{7,14}$'", name="telefono_e164"),
        CheckConstraint("estado IN ('ACTIVA','BAJA')", name="estado_valido"),
        CheckConstraint(
            "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL "
            "AND baja_por_id IS NOT NULL) OR (estado = 'ACTIVA' AND fecha_baja IS NULL "
            "AND motivo_baja IS NULL AND baja_por_id IS NULL)",
            name="datos_de_baja_coherentes",
        ),
        Index("ix_sede_estado_nombre", "estado", "nombre"),
        Index("ix_sede_direccion_normalizada", "direccion_normalizada"),
    )

    codigo: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    calle: Mapped[str] = mapped_column(String(100), nullable=False)
    numero: Mapped[str] = mapped_column(String(10), nullable=False)
    localidad_id: Mapped[int] = mapped_column(ForeignKey("localidad.id"), nullable=False)
    direccion_normalizada: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[str] = mapped_column(String(16), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    responsable: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, server_default="ACTIVA")
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_baja: Mapped[str | None] = mapped_column(String(300))
    baja_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    actualizado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    localidad: Mapped[LocalidadORM] = relationship(lazy="joined")
    horarios: Mapped[list["HorarioSedeORM"]] = relationship(
        cascade="all, delete-orphan",
        order_by="HorarioSedeORM.dia_semana, HorarioSedeORM.hora_apertura",
    )
    excepciones: Mapped[list["ExcepcionHorarioSedeORM"]] = relationship(
        cascade="all, delete-orphan",
        order_by="ExcepcionHorarioSedeORM.fecha, ExcepcionHorarioSedeORM.hora_desde",
    )


class HorarioSedeORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "horario_sede"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 1 AND 7", name="dia_valido"),
        CheckConstraint("hora_cierre > hora_apertura", name="cierre_posterior"),
        Index("ix_horario_sede_sede_id_dia_semana", "sede_id", "dia_semana"),
    )

    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hora_apertura: Mapped[time] = mapped_column(Time, nullable=False)
    hora_cierre: Mapped[time] = mapped_column(Time, nullable=False)


class ExcepcionHorarioSedeORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "excepcion_horario_sede"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'CIERRE_TOTAL' AND hora_desde IS NULL AND hora_hasta IS NULL) OR "
            "(tipo = 'CIERRE_PARCIAL' AND hora_desde IS NOT NULL AND hora_hasta IS NOT NULL "
            "AND hora_desde < hora_hasta)",
            name="tipo_coherente",
        ),
        Index("ix_excepcion_horario_sede_sede_id_fecha", "sede_id", "fecha"),
    )

    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    hora_desde: Mapped[time | None] = mapped_column(Time)
    hora_hasta: Mapped[time | None] = mapped_column(Time)
    motivo: Mapped[str | None] = mapped_column(String(150))
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)


class HistorialSedeORM(ConAuditoriaDeTiempo, Base):
    """Auditoría de solo inserción de las sedes (un disparador impide UPDATE y DELETE)."""

    __tablename__ = "historial_sede"
    __table_args__ = (
        CheckConstraint(
            "tipo_evento IN ('ALTA','MODIFICACION','BAJA','REACTIVACION',"
            "'EXCEPCION_AGREGADA','EXCEPCION_ELIMINADA')",
            name="tipo_evento_valido",
        ),
        Index("ix_historial_sede_sede_id_fecha_hora", "sede_id", text("fecha_hora DESC")),
    )

    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(25), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    estado_anterior: Mapped[str | None] = mapped_column(String(10))
    estado_nuevo: Mapped[str | None] = mapped_column(String(10))
    motivo: Mapped[str | None] = mapped_column(String(300))
    cambios: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    version_resultante: Mapped[int] = mapped_column(Integer, nullable=False)
