"""Catálogo cerrado de provincias y localidades."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo


class ProvinciaORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "provincia"

    nombre: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)


class LocalidadORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "localidad"
    __table_args__ = (UniqueConstraint("provincia_id", "nombre", "departamento"),)

    provincia_id: Mapped[int] = mapped_column(ForeignKey("provincia.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    departamento: Mapped[str] = mapped_column(String(60), nullable=False)

    provincia: Mapped[ProvinciaORM] = relationship(lazy="joined")
