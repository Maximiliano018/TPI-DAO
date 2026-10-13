from typing import Any

from fastapi import APIRouter, Depends

from biblioteca.api.deps import ROLES_ATENCION, Ahora, Alcance, Db, Pagina, requiere_rol
from biblioteca.api.schemas.circulacion import DevolucionOut, PrestamoOut, ReservaOut
from biblioteca.application.services.devoluciones import listar_devoluciones
from biblioteca.application.services.prestamos import listar_prestamos
from biblioteca.application.services.reservas import listar_reservas
from biblioteca.domain.enums import EstadoPrestamo, EstadoReserva

# Circulación es del ADMIN y los bibliotecarios; cada uno ve los datos de su sede.
router = APIRouter(tags=["circulación"], dependencies=[Depends(requiere_rol(*ROLES_ATENCION))])


@router.get("/prestamos", response_model=list[PrestamoOut])
def get_prestamos(
    db: Db,
    ahora: Ahora,
    pagina: Pagina,
    alcance: Alcance,
    estado: EstadoPrestamo | None = None,
    abiertos: bool = False,
) -> list[dict[str, Any]]:
    """`abiertos=true`: solo en envío, listos para retiro y activos."""
    return listar_prestamos(
        db, ahora.date(), estado, abiertos, pagina.limit, pagina.offset, sede_id=alcance
    )


@router.get("/reservas", response_model=list[ReservaOut])
def get_reservas(
    db: Db, alcance: Alcance, estado: EstadoReserva | None = None, abiertas: bool = False
) -> list[dict[str, Any]]:
    """`abiertas=true`: solo pendientes y asignadas."""
    return listar_reservas(db, estado, abiertas, sede_id=alcance)


@router.get("/devoluciones", response_model=list[DevolucionOut])
def get_devoluciones(db: Db, pagina: Pagina, alcance: Alcance) -> list[dict[str, Any]]:
    return listar_devoluciones(db, pagina.limit, pagina.offset, sede_id=alcance)
