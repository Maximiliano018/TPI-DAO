"""Tablas de devoluciones y multas."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.prestamo import PrestamoORM


class DevolucionORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "devolucion"
    __table_args__ = (
        CheckConstraint(
            "estado_fisico_recibido IN ('BUENO','REGULAR','DANADO','EXTRAVIADO')",
            name="estado_valido",
        ),
        CheckConstraint("dias_atraso >= 0", name="atraso_no_negativo"),
    )

    prestamo_id: Mapped[int] = mapped_column(ForeignKey("prestamo.id"), nullable=False, unique=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado_fisico_recibido: Mapped[str] = mapped_column(String(15), nullable=False)
    dias_atraso: Mapped[int] = mapped_column(Integer, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(300))
    registrada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


class MultaORM(ConAuditoriaDeTiempo, Base):
    """Multa por atraso. Guarda el monto por día vigente al generarse (no cambia después)."""

    __tablename__ = "multa"
    __table_args__ = (
        CheckConstraint("estado IN ('PENDIENTE','SALDADA')", name="estado_valido"),
        CheckConstraint("monto_total >= 0", name="monto_no_negativo"),
        CheckConstraint(
            "(estado = 'SALDADA') = (fecha_saldada IS NOT NULL)", name="saldada_con_fecha"
        ),
        Index("ix_multa_socio_id_estado", "socio_id", "estado"),
    )

    prestamo_id: Mapped[int] = mapped_column(ForeignKey("prestamo.id"), nullable=False, unique=True)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socio.id"), nullable=False)
    dias_atraso: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_por_dia: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_saldada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    saldada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    prestamo: Mapped["PrestamoORM"] = relationship(lazy="joined")
