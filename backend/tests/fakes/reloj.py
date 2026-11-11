"""Reloj controlable para las pruebas."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Argentina/Cordoba")


class RelojFijo:
    """Implementa ``Reloj`` con un momento fijo que se puede avanzar."""

    def __init__(self, local: datetime | None = None) -> None:
        self._local = local or datetime(2026, 11, 10, 12, 0, tzinfo=ZONA)

    def ahora(self) -> datetime:
        return self._local.astimezone(UTC)

    def ahora_local(self) -> datetime:
        return self._local

    def hoy(self) -> date:
        return self._local.date()

    def avanzar(self, **delta: int) -> None:
        """Avanza el reloj (``dias=1``, ``horas=2``...)."""
        self._local += timedelta(
            **{k.replace("dias", "days").replace("horas", "hours"): v for k, v in delta.items()}
        )
