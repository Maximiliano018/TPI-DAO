"""Tareas periódicas del backend (decisión D7: APScheduler dentro del proceso).

Cada tarea corre una vez al iniciar y después todos los días a las 00:05 (hora de negocio). Usa
los mismos casos de uso que el endpoint administrativo, con su propia sesión y transacción.
No se programan en las pruebas (``ENTORNO=test``): ahí se llaman directamente.
"""

import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import Settings
from app.db.session import crear_fabrica_sesiones
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWork
from app.services.prestamo_service import PrestamoService
from app.services.reserva_service import ReservaService
from app.utils.reloj import Reloj, RelojSistema

logger = logging.getLogger(__name__)

TAREAS: list[tuple[str, Callable[[UnitOfWork, Reloj], int]]] = [
    ("préstamos vencidos", lambda uow, reloj: PrestamoService(uow, reloj).detectar_vencidos()),
    ("reservas vencidas", lambda uow, reloj: ReservaService(uow, reloj).vencer_reservas()),
]


def ejecutar_tareas(settings: Settings) -> None:
    """Corre cada tarea en su propia sesión; un error en una no detiene a las demás."""
    reloj = RelojSistema(settings.tz_negocio)
    for nombre, tarea in TAREAS:
        with crear_fabrica_sesiones()() as sesion:
            try:
                cantidad = tarea(SqlAlchemyUnitOfWork(sesion), reloj)
                logger.info("Tarea %s: %s cambios", nombre, cantidad)
            except Exception:
                logger.exception("Falló la tarea %s", nombre)


def iniciar_programador(settings: Settings) -> BackgroundScheduler | None:
    """Arranca el programador de tareas (salvo en las pruebas)."""
    if settings.entorno == "test":
        return None
    programador = BackgroundScheduler(timezone=settings.tz_negocio)
    programador.add_job(ejecutar_tareas, "cron", hour=0, minute=5, args=[settings])
    programador.add_job(ejecutar_tareas, args=[settings])  # una vez al iniciar
    programador.start()
    return programador
