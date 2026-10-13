from datetime import date, datetime
from typing import Protocol


class Reloj(Protocol):
    """Fuente única de "ahora" y "hoy" para el dominio.

    El dominio nunca llama a `datetime.now()` ni a `date.today()`: recibe un Reloj.
    Así los tests fijan la fecha y las reglas de vencimiento son reproducibles.
    """

    def ahora(self) -> datetime:
        """Instante actual con zona horaria."""
        ...

    def hoy(self) -> date:
        """Fecha de negocio actual, en la zona horaria de la red de bibliotecas."""
        ...
