"""Reloj inyectable: el dominio nunca llama a ``datetime.now()`` directamente."""

from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Reloj(Protocol):
    """Fuente de la hora actual."""

    def ahora(self) -> datetime:
        """Momento actual con zona horaria UTC."""
        ...

    def hoy(self) -> date:
        """Fecha actual en la zona de negocio."""
        ...

    def ahora_local(self) -> datetime:
        """Momento actual en la zona de negocio."""
        ...


class RelojSistema:
    """Reloj real, con la zona de negocio configurada."""

    def __init__(self, zona: str = "America/Argentina/Cordoba") -> None:
        self._zona = ZoneInfo(zona)

    def ahora(self) -> datetime:
        return datetime.now(UTC)

    def ahora_local(self) -> datetime:
        return datetime.now(self._zona)

    def hoy(self) -> date:
        return self.ahora_local().date()
