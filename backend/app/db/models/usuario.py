"""Usuarios del sistema (personal y cuentas de socio)."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.sede import SedeORM


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

    sede: Mapped["SedeORM | None"] = relationship(foreign_keys=[sede_id], lazy="joined")
