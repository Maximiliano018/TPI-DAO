"""Tablas del catálogo: categorías, autores, libros y ejemplares con su historial."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ConAuditoriaDeTiempo

if TYPE_CHECKING:
    from app.db.models.sede import SedeORM

ESTADOS_EJEMPLAR = (
    "'DISPONIBLE','APARTADO','RESERVADO','PRESTADO','EN_TRANSITO','EN_REVISION','BAJA'"
)


class CategoriaORM(ConAuditoriaDeTiempo, Base):
    """Catálogo cerrado de categorías (se carga con una migración de datos)."""

    __tablename__ = "categoria"

    nombre: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)


class AutorORM(ConAuditoriaDeTiempo, Base):
    __tablename__ = "autor"

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class LibroAutorORM(Base):
    """Autores de un libro, en el orden en que figuran en la obra."""

    __tablename__ = "libro_autor"

    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libro.id", ondelete="CASCADE"), primary_key=True
    )
    autor_id: Mapped[int] = mapped_column(ForeignKey("autor.id"), primary_key=True)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    autor: Mapped[AutorORM] = relationship(lazy="joined")


class LibroORM(ConAuditoriaDeTiempo, Base):
    """Obra del catálogo. Con ISBN se identifica por él; sin ISBN, por su clave natural."""

    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint(
            "tipo_material IN ('LIBRO','REVISTA','OBRA_DE_REFERENCIA','OTRO')",
            name="tipo_material_valido",
        ),
        CheckConstraint("(isbn IS NULL) = (clave_natural IS NOT NULL)", name="isbn_o_clave"),
        Index("ix_libro_titulo_normalizado", "titulo_normalizado"),
    )

    isbn: Mapped[str | None] = mapped_column(String(13), unique=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    titulo_normalizado: Mapped[str] = mapped_column(String(200), nullable=False)
    editorial: Mapped[str | None] = mapped_column(String(100))
    anio_edicion: Mapped[int | None] = mapped_column(SmallInteger)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"), nullable=False)
    tipo_material: Mapped[str] = mapped_column(String(20), nullable=False)
    clave_natural: Mapped[str | None] = mapped_column(String(420), unique=True)
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    categoria: Mapped[CategoriaORM] = relationship(lazy="joined")
    autores: Mapped[list[LibroAutorORM]] = relationship(
        order_by=LibroAutorORM.orden, cascade="all, delete-orphan", lazy="selectin"
    )


class EjemplarORM(ConAuditoriaDeTiempo, Base):
    """Copia física. Pertenece a una sede (propietaria) y está en otra (actual)."""

    __tablename__ = "ejemplar"
    __table_args__ = (
        CheckConstraint(
            "estado_fisico IN ('NUEVO','BUENO','REGULAR','DANADO')", name="estado_fisico_valido"
        ),
        CheckConstraint(f"estado IN ({ESTADOS_EJEMPLAR})", name="estado_valido"),
        CheckConstraint(
            "(estado = 'BAJA') = (fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL)",
            name="baja_con_datos",
        ),
        CheckConstraint("codigo_inventario ~ '^[A-Z0-9][A-Z0-9-]{2,29}$'", name="codigo_formato"),
        Index("ix_ejemplar_libro_id_sede_actual_id_estado", "libro_id", "sede_actual_id", "estado"),
        Index("ix_ejemplar_sede_propietaria_id_estado", "sede_propietaria_id", "estado"),
    )

    codigo_inventario: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    libro_id: Mapped[int] = mapped_column(ForeignKey("libro.id"), nullable=False)
    sede_propietaria_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    sede_actual_id: Mapped[int] = mapped_column(ForeignKey("sede.id"), nullable=False)
    estado_fisico: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(300))
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_baja: Mapped[str | None] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    libro: Mapped[LibroORM] = relationship(lazy="joined")
    sede_propietaria: Mapped["SedeORM"] = relationship(
        foreign_keys=[sede_propietaria_id], lazy="joined"
    )
    sede_actual: Mapped["SedeORM"] = relationship(foreign_keys=[sede_actual_id], lazy="joined")


class MovimientoEjemplarORM(Base):
    """Historial de estados del ejemplar, de solo inserción (un disparador lo protege)."""

    __tablename__ = "movimiento_ejemplar"
    __table_args__ = (
        Index("ix_movimiento_ejemplar_ejemplar_id_fecha_hora", "ejemplar_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ejemplar_id: Mapped[int] = mapped_column(ForeignKey("ejemplar.id"), nullable=False)
    estado_anterior: Mapped[str | None] = mapped_column(String(15))
    estado_nuevo: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    observacion: Mapped[str | None] = mapped_column(Text)


__all__ = [
    "AutorORM",
    "CategoriaORM",
    "EjemplarORM",
    "LibroAutorORM",
    "LibroORM",
    "MovimientoEjemplarORM",
]
