from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, String
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


class TextoEnum[E: StrEnum](TypeDecorator[E]):
    """Columna de texto que se lee como la enumeración del dominio.

    En la base es un VARCHAR común (los valores válidos los restringe un CHECK). Al
    escribir acepta la enumeración o su texto; un texto inválido llega a la base y lo
    rechaza el CHECK, que es la red de seguridad.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum: type[E], largo: int) -> None:
        super().__init__(largo)
        self.enum = enum

    def process_bind_param(self, value: E | str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return value.value if isinstance(value, self.enum) else str(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> E | None:
        return None if value is None else self.enum(value)
