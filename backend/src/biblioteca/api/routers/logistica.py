from typing import Any

from fastapi import APIRouter, Depends

from biblioteca.api.deps import Ahora, Alcance, Db, Pagina, usuario_actual
from biblioteca.api.schemas.logistica import MovimientoRemitoOut, RemitoOut
from biblioteca.application.services.remitos import listar_remitos, movimientos_de_remito
from biblioteca.domain.enums import EstadoRemito, Sentido

# Logística la ven todos los roles; cada uno, los envíos que involucran a su sede.
router = APIRouter(tags=["logística"], dependencies=[Depends(usuario_actual)])


@router.get("/remitos", response_model=list[RemitoOut])
def get_remitos(
    db: Db,
    ahora: Ahora,
    pagina: Pagina,
    alcance: Alcance,
    estado: EstadoRemito | None = None,
    sentido: Sentido | None = None,
) -> list[dict[str, Any]]:
    return listar_remitos(db, ahora, estado, sentido, pagina.limit, pagina.offset, sede_id=alcance)


@router.get("/remitos/{remito_id}/movimientos", response_model=list[MovimientoRemitoOut])
def get_movimientos_remito(db: Db, alcance: Alcance, remito_id: int) -> list[dict[str, Any]]:
    """Trazabilidad: cada cambio de estado con fecha, hora y responsable."""
    return movimientos_de_remito(db, remito_id, sede_id=alcance)
