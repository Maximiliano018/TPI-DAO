from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


class RelojSistema:
    """Reloj real. "Hoy" se calcula en la zona horaria de la red, no en UTC: a las 22 h
    de Argentina ya es el día siguiente en UTC, y los vencimientos son por día local."""

    def __init__(self, zona_horaria: str) -> None:
        self.zona = ZoneInfo(zona_horaria)

    def ahora(self) -> datetime:
        return datetime.now(UTC)

    def hoy(self) -> date:
        return datetime.now(self.zona).date()
