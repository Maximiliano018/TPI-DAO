from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class FechaHoraUTC(TypeDecorator[datetime]):
    """Instante guardado en UTC.

    SQLite no guarda zona horaria: se persiste la hora UTC sin zona y al leerla se
    le vuelve a poner UTC. Rechaza datetimes sin zona para no mezclar horas locales.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Se requiere un datetime con zona horaria (usar el Reloj del dominio)")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
