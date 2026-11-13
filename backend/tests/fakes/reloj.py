"""Relojes para las pruebas."""

import time as _tiempo
from datetime import UTC, date, datetime, time, timedelta
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


class RelojDePruebas:
    """Reloj de las pruebas de la API: arranca hoy a las 12:00 (zona de negocio) y avanza.

    Las pruebas calculan fechas esperadas («hoy + 14 días») y la API usa su propio reloj. Con el
    reloj real, una corrida que cruza la medianoche de Córdoba (en el CI, que corre en UTC, pasa
    a las 3 de la mañana) ve dos «hoy» distintos. Arrancando al mediodía y avanzando con el tiempo
    transcurrido, la fecha no cambia durante la corrida y el orden de los eventos se conserva.
    """

    def __init__(self) -> None:
        self._inicio = datetime.combine(datetime.now(ZONA).date(), time(12), ZONA)
        self._t0 = _tiempo.monotonic()

    def ahora_local(self) -> datetime:
        return self._inicio + timedelta(seconds=_tiempo.monotonic() - self._t0)

    def ahora(self) -> datetime:
        return self.ahora_local().astimezone(UTC)

    def hoy(self) -> date:
        return self.ahora_local().date()


RELOJ_DE_PRUEBAS = RelojDePruebas()
HOY_DE_PRUEBAS = RELOJ_DE_PRUEBAS.hoy()
