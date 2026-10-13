from typing import Any

from fastapi import APIRouter, Depends, status

from biblioteca.api.deps import Admin, AdminOBibliotecario, Ahora, Db, Pagina, Uow, usuario_actual
from biblioteca.api.schemas.organizacion import (
    DatosSedeIn,
    HorarioIn,
    SedeIn,
    SedeOut,
    SocioOut,
)
from biblioteca.application.services.sedes import (
    actualizar_sede,
    dar_de_baja_sede,
    definir_horarios,
    listar_sedes,
    obtener_sede,
    reactivar_sede,
    registrar_sede,
)
from biblioteca.application.services.socios import listar_socios

# Toda la sección exige sesión; los comandos piden además un rol.
router = APIRouter(tags=["organización"], dependencies=[Depends(usuario_actual)])

# ------------------------------------------------------------------------------- Sedes
# Las sedes las consulta todo el personal; el ABM es del ADMIN.


@router.get("/sedes", response_model=list[SedeOut])
def get_sedes(db: Db) -> list[dict[str, Any]]:
    return listar_sedes(db)


@router.get("/sedes/{sede_id}", response_model=SedeOut)
def get_sede(db: Db, sede_id: int) -> dict[str, Any]:
    return obtener_sede(db, sede_id)


@router.post("/sedes", response_model=SedeOut, status_code=status.HTTP_201_CREATED)
def post_sede(uow: Uow, db: Db, actor: Admin, datos: SedeIn) -> dict[str, Any]:
    """Alta de sede. 409 si el código o el nombre ya existen."""
    sede_id = registrar_sede(uow, actor, datos.codigo, datos.a_datos())
    return obtener_sede(db, sede_id)


@router.put("/sedes/{sede_id}", response_model=SedeOut)
def put_sede(uow: Uow, db: Db, actor: Admin, sede_id: int, datos: DatosSedeIn) -> dict[str, Any]:
    """Modifica los datos de contacto. El código no se cambia."""
    actualizar_sede(uow, actor, sede_id, datos.a_datos())
    return obtener_sede(db, sede_id)


@router.put("/sedes/{sede_id}/horarios", response_model=SedeOut)
def put_horarios(
    uow: Uow, db: Db, actor: Admin, sede_id: int, franjas: list[HorarioIn]
) -> dict[str, Any]:
    """Reemplaza todos los horarios. 422 si hay franjas superpuestas el mismo día."""
    definir_horarios(uow, actor, sede_id, [f.a_franja() for f in franjas])
    return obtener_sede(db, sede_id)


@router.post("/sedes/{sede_id}/baja", response_model=SedeOut)
def post_baja_sede(uow: Uow, db: Db, actor: Admin, ahora: Ahora, sede_id: int) -> dict[str, Any]:
    """409 si la sede tiene préstamos, envíos o reservas en curso."""
    dar_de_baja_sede(uow, actor, sede_id, ahora)
    return obtener_sede(db, sede_id)


@router.post("/sedes/{sede_id}/reactivar", response_model=SedeOut)
def post_reactivar_sede(uow: Uow, db: Db, actor: Admin, sede_id: int) -> dict[str, Any]:
    reactivar_sede(uow, actor, sede_id)
    return obtener_sede(db, sede_id)


# ------------------------------------------------------------------------------ Socios


@router.get("/socios", response_model=list[SocioOut])
def get_socios(
    db: Db, pagina: Pagina, _actor: AdminOBibliotecario, buscar: str | None = None
) -> list[dict[str, Any]]:
    """Busca por DNI, número de socio, nombre o apellido. Los socios son de toda la red."""
    return listar_socios(db, buscar, pagina.limit, pagina.offset)
