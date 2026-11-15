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
    UniqueConstraint,
    text,
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
        # Una fecha anterior al registro (retroactiva) exige su motivo (RF-DEV-14).
        CheckConstraint(
            "motivo_fecha IS NOT NULL OR fecha_hora >= registrada_en - interval '1 day'",
            name="retroactiva_con_motivo",
        ),
    )

    prestamo_id: Mapped[int] = mapped_column(ForeignKey("prestamo.id"), nullable=False, unique=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado_fisico_recibido: Mapped[str] = mapped_column(String(15), nullable=False)
    dias_atraso: Mapped[int] = mapped_column(Integer, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(300))
    registrada_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo_fecha: Mapped[str | None] = mapped_column(String(300))


TIPOS_MULTA = "'ATRASO','DANIO','EXTRAVIO'"


class MultaORM(ConAuditoriaDeTiempo, Base):
    """Multa de un préstamo: por atraso (guarda el monto por día vigente al generarse) o por
    daño o extravío del ejemplar. Un préstamo tiene a lo sumo una de cada tipo."""

    __tablename__ = "multa"
    __table_args__ = (
        UniqueConstraint("prestamo_id", "tipo"),
        CheckConstraint("estado IN ('PENDIENTE','SALDADA')", name="estado_valido"),
        CheckConstraint(f"tipo IN ({TIPOS_MULTA})", name="tipo_valido"),
        CheckConstraint("monto_total >= 0", name="monto_no_negativo"),
        CheckConstraint(
            "(estado = 'SALDADA') = (fecha_saldada IS NOT NULL)", name="saldada_con_fecha"
        ),
        # Solo la de atraso tiene días y monto por día.
        CheckConstraint(
            "(tipo = 'ATRASO') = (dias_atraso IS NOT NULL AND monto_por_dia IS NOT NULL)",
            name="atraso_segun_tipo",
        ),
        # La de atraso existe solo con atraso, y el total no supera días × monto (menos con tope).
        CheckConstraint("dias_atraso IS NULL OR dias_atraso > 0", name="atraso_positivo"),
        CheckConstraint(
            "dias_atraso IS NULL "
            "OR (monto_por_dia >= 0 AND monto_total <= dias_atraso * monto_por_dia)",
            name="monto_coherente",
        ),
        Index("ix_multa_socio_id_estado", "socio_id", "estado"),
    )

    prestamo_id: Mapped[int] = mapped_column(ForeignKey("prestamo.id"), nullable=False)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socio.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    dias_atraso: Mapped[int | None] = mapped_column(Integer)
    monto_por_dia: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    monto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_saldada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    saldada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    prestamo: Mapped["PrestamoORM"] = relationship(lazy="joined")


MEDIOS_PAGO = "'EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA','EN_LINEA','NO_REGISTRADO'"
ESTADOS_PAGO = "'PENDIENTE','APROBADO','RECHAZADO','CANCELADO'"


class PagoORM(ConAuditoriaDeTiempo, Base):
    """Pago de una multa: en el mostrador o en línea (simulado).

    Una multa tiene a lo sumo un pago aprobado y un pago en línea pendiente.
    """

    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint(f"medio IN ({MEDIOS_PAGO})", name="medio_valido"),
        CheckConstraint(f"estado IN ({ESTADOS_PAGO})", name="estado_valido"),
        CheckConstraint("monto > 0", name="monto_positivo"),
        # El de mostrador nace aprobado y lo registra alguien; solo el en línea pasa por estados.
        CheckConstraint(
            "medio = 'EN_LINEA' OR (estado = 'APROBADO' "
            "AND (registrado_por_id IS NOT NULL OR medio = 'NO_REGISTRADO'))",
            name="mostrador_aprobado",
        ),
        CheckConstraint(
            "(estado = 'APROBADO') = (acreditado_en IS NOT NULL)",
            name="acreditado_segun_estado",
        ),
        # Del pago en línea: la forma elegida y, con tarjeta, solo sus últimos 4 dígitos.
        CheckConstraint(
            "forma_en_linea IS NULL OR (medio = 'EN_LINEA' AND forma_en_linea IN "
            "('TARJETA_CREDITO','TARJETA_DEBITO','DINERO_EN_CUENTA'))",
            name="forma_en_linea_valida",
        ),
        CheckConstraint(
            "(tarjeta_ultimos4 IS NOT NULL) = "
            "(forma_en_linea IN ('TARJETA_CREDITO','TARJETA_DEBITO')) "
            "AND (tarjeta_ultimos4 IS NULL OR tarjeta_ultimos4 ~ '^[0-9]{4}$')",
            name="tarjeta_segun_forma",
        ),
        Index(
            "uq_pago_aprobado_por_multa",
            "multa_id",
            unique=True,
            postgresql_where=text("estado = 'APROBADO'"),
        ),
        Index(
            "uq_pago_pendiente_por_multa",
            "multa_id",
            unique=True,
            postgresql_where=text("estado = 'PENDIENTE'"),
        ),
    )

    multa_id: Mapped[int] = mapped_column(ForeignKey("multa.id"), nullable=False)
    medio: Mapped[str] = mapped_column(String(15), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    comprobante: Mapped[str | None] = mapped_column(String(100))
    motivo: Mapped[str | None] = mapped_column(String(120))
    forma_en_linea: Mapped[str | None] = mapped_column(String(20))
    tarjeta_ultimos4: Mapped[str | None] = mapped_column(String(4))
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acreditado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
