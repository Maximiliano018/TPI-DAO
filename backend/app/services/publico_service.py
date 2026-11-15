"""Lo que muestra la página de inicio pública, antes de ingresar.

Solo datos de la colección (cuántas sedes, libros y ejemplares tiene la red y los libros más
pedidos): nada de socios ni de préstamos individuales. Es una consulta de solo lectura.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AutorORM, EjemplarORM, LibroAutorORM, LibroORM, PrestamoORM, SedeORM
from app.utils.reloj import Reloj

DIAS_DE_DESTACADOS = 120


@dataclass(frozen=True)
class LibroDestacado:
    libro_id: int
    titulo: str
    autores: list[str]
    portada_url: str | None
    pedidos: int


@dataclass(frozen=True)
class InicioPublico:
    sedes_activas: int
    libros: int
    ejemplares: int
    destacados: list[LibroDestacado] = field(default_factory=list)


class PublicoService:
    def __init__(self, sesion: Session, reloj: Reloj) -> None:
        self._sesion = sesion
        self._reloj = reloj

    def inicio(self, limite: int = 12) -> InicioPublico:
        """Resumen de la red y los libros más pedidos de los últimos meses.

        Cuenta los préstamos no cancelados de los últimos ``DIAS_DE_DESTACADOS`` días. Si hay
        menos libros pedidos que ``limite``, completa con los últimos incorporados al catálogo,
        para que la página nunca quede vacía.
        """
        desde = self._reloj.ahora() - timedelta(days=DIAS_DE_DESTACADOS)
        pedidos = func.count(PrestamoORM.id)
        ranking = self._sesion.execute(
            select(LibroORM.id, pedidos)
            .join(EjemplarORM, EjemplarORM.libro_id == LibroORM.id)
            .join(PrestamoORM, PrestamoORM.ejemplar_id == EjemplarORM.id)
            .where(PrestamoORM.estado != "CANCELADO", PrestamoORM.fecha_solicitud >= desde)
            .group_by(LibroORM.id)
            .order_by(pedidos.desc(), LibroORM.id)
            .limit(limite)
        ).all()
        conteo = {libro_id: cantidad for libro_id, cantidad in ranking}
        ids = list(conteo)
        if len(ids) < limite:
            ids += self._sesion.scalars(
                select(LibroORM.id)
                .where(LibroORM.id.not_in(ids))
                .order_by(LibroORM.id.desc())
                .limit(limite - len(ids))
            ).all()
        return InicioPublico(
            sedes_activas=self._contar(
                select(func.count(SedeORM.id)).where(SedeORM.estado == "ACTIVA")
            ),
            libros=self._contar(select(func.count(LibroORM.id))),
            ejemplares=self._contar(
                select(func.count(EjemplarORM.id))
                .join(SedeORM, SedeORM.id == EjemplarORM.sede_actual_id)
                .where(EjemplarORM.estado != "BAJA", SedeORM.estado == "ACTIVA")
            ),
            destacados=self._destacados(ids, conteo),
        )

    def _destacados(self, ids: list[int], conteo: dict[int, int]) -> list[LibroDestacado]:
        if not ids:
            return []
        libros = {
            libro.id: libro
            for libro in self._sesion.scalars(select(LibroORM).where(LibroORM.id.in_(ids)))
        }
        autores: dict[int, list[str]] = {i: [] for i in ids}
        for libro_id, nombre in self._sesion.execute(
            select(LibroAutorORM.libro_id, AutorORM.nombre)
            .join(AutorORM, AutorORM.id == LibroAutorORM.autor_id)
            .where(LibroAutorORM.libro_id.in_(ids))
            .order_by(LibroAutorORM.libro_id, LibroAutorORM.orden)
        ):
            autores[libro_id].append(nombre)
        return [
            LibroDestacado(
                libro_id=i,
                titulo=libros[i].titulo,
                autores=autores[i],
                portada_url=libros[i].portada_url,
                pedidos=conteo.get(i, 0),
            )
            for i in ids
            if i in libros
        ]

    def _contar(self, consulta) -> int:  # type: ignore[no-untyped-def]
        return int(self._sesion.scalar(consulta) or 0)
