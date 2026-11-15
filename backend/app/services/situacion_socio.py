"""Reevaluación del socio después de un evento que cambia sus causas de inhabilitación."""

from datetime import datetime

from app.models.socio import Socio
from app.models.usuario import UsuarioRef
from app.repositories.unit_of_work import UnitOfWork


def reevaluar_socio(
    uow: UnitOfWork, socio_id: int, actor: UsuarioRef | None, ahora: datetime, origen: str
) -> Socio | None:
    """Recalcula su estado con la situación vigente (RF-SOC-05) y lo guarda si cambió."""
    socio = uow.socios.obtener_para_modificar(socio_id)
    if socio is None:
        return None
    situacion = uow.socios.situacion(socio_id)
    if socio.reevaluar(situacion, actor=actor, ahora=ahora, origen=origen):
        uow.socios.guardar(socio)
    return socio
