"""Base declarativa de los modelos ORM."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base de todas las tablas, con nombres de restricciones estables."""

    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


class ConAuditoriaDeTiempo:
    """Mixin con ``id``, ``creado_en`` y ``actualizado_en`` (convención de todas las tablas)."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
