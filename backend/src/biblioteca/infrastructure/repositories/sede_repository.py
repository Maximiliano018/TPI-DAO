from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from biblioteca.domain.entities.sede import Sede
from biblioteca.domain.enums import (
    ESTADOS_PRESTAMO_ABIERTOS,
    ESTADOS_REMITO_NO_FINALES,
    ESTADOS_RESERVA_ABIERTOS,
)
from biblioteca.infrastructure.db import tables as t


class SqlAlchemySedeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def agregar(self, sede: Sede) -> None:
        self.session.add(sede)

    def obtener(self, sede_id: int) -> Sede | None:
        return self.session.get(Sede, sede_id)

    def existe_codigo(self, codigo: str) -> bool:
        return bool(self.session.scalar(select(exists().where(t.sede.c.codigo == codigo))))

    def existe_nombre(self, nombre: str, excepto_id: int | None = None) -> bool:
        condicion = func.lower(t.sede.c.nombre) == nombre.lower()
        if excepto_id is not None:
            condicion = condicion & (t.sede.c.id != excepto_id)
        return bool(self.session.scalar(select(exists().where(condicion))))

    def listar(self, *, solo_activas: bool, limite: int, desde: int) -> list[Sede]:
        consulta = select(Sede).order_by(t.sede.c.nombre).limit(limite).offset(desde)
        if solo_activas:
            consulta = consulta.where(t.sede.c.activa.is_(True))
        return list(self.session.scalars(consulta))

    def contar(self, *, solo_activas: bool) -> int:
        consulta = select(func.count()).select_from(t.sede)
        if solo_activas:
            consulta = consulta.where(t.sede.c.activa.is_(True))
        return int(self.session.scalar(consulta) or 0)

    def tiene_actividad_abierta(self, sede_id: int) -> bool:
        prestamos = exists().where(
            or_(t.prestamo.c.sede_origen_id == sede_id, t.prestamo.c.sede_destino_id == sede_id),
            t.prestamo.c.estado.in_(ESTADOS_PRESTAMO_ABIERTOS),
        )
        remitos = exists().where(
            or_(t.remito.c.sede_origen_id == sede_id, t.remito.c.sede_destino_id == sede_id),
            t.remito.c.estado.in_(ESTADOS_REMITO_NO_FINALES),
        )
        reservas = exists().where(
            t.reserva.c.sede_id == sede_id,
            t.reserva.c.estado.in_(ESTADOS_RESERVA_ABIERTOS),
        )
        return bool(self.session.scalar(select(or_(prestamos, remitos, reservas))))
