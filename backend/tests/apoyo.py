"""Dobles de prueba compartidos."""

from datetime import UTC, date, datetime, timedelta


class RelojFijo:
    """Reloj controlable: los tests fijan "ahora" y lo adelantan a voluntad."""

    def __init__(self, ahora: datetime = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def hoy(self) -> date:
        # Los tests usan horarios de la tarde en UTC: la fecha coincide con la local.
        return self._ahora.date()

    def adelantar(self, **delta: float) -> None:
        self._ahora += timedelta(**delta)


class HasherDePrueba:
    """Hasher trivial para tests que no prueban el hash: argon2 es lento a propósito."""

    def hashear(self, contrasena: str) -> str:
        return f"hash:{contrasena}"

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return hash_guardado == f"hash:{contrasena}"
