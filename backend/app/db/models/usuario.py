"""Usuarios del sistema y socios (estructura mínima para el vínculo usuario-socio)."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ConAuditoriaDeTiempo


class SocioORM(ConAuditoriaDeTiempo, Base):
    """Socio de la red. El módulo de socios completa la lógica; acá solo la estructura."""

    __tablename__ = "socio"
    __table_args__ = (
        UniqueConstraint("tipo_documento", "nro_documento"),
        CheckConstraint("estado IN ('HABILITADO','INHABILITADO')", name="estado_valido"),
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
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsuarioORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("username ~ '^[a-z0-9._-]{3,50}$'", name="username_formato"),
        CheckConstraint("rol IN ('ADMIN','BIBLIOTECARIO','SOCIO')", name="rol_valido"),
        CheckConstraint(
            "rol <> 'BIBLIOTECARIO' OR sede_id IS NOT NULL", name="bibliotecario_con_sede"
        ),
        CheckConstraint("rol <> 'ADMIN' OR sede_id IS NULL", name="admin_sin_sede"),
        CheckConstraint("(rol = 'SOCIO') = (socio_id IS NOT NULL)", name="socio_con_ficha"),
        Index(
            "ix_usuario_bibliotecarios_activos_por_sede",
            "sede_id",
            postgresql_where=text("rol = 'BIBLIOTECARIO' AND activo"),
        ),
    )

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    rol: Mapped[str] = mapped_column(String(15), nullable=False)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sede.id"))
    socio_id: Mapped[int | None] = mapped_column(ForeignKey("socio.id"), unique=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
