"""Endpoints del catálogo: categorías, libros, disponibilidad y ejemplares."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import get_catalogo_service, requiere
from app.dtos.request.catalogo_request import (
    EjemplarBajaRequest,
    EjemplarCrearRequest,
    EjemplarModificarRequest,
    LibroModificarRequest,
    LibroRequest,
    RecuperarEjemplarRequest,
    VersionRequest,
)
from app.dtos.response.catalogo_response import (
    CategoriaResponse,
    DisponibilidadResponse,
    EjemplarDetalleResponse,
    EjemplarResponse,
    LibroResponse,
    PaginaEjemplaresResponse,
    PaginaLibrosResponse,
    libro_a_response,
)
from app.models.libro import TipoMaterial
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.usuario import Permiso, Usuario
from app.services.catalogo_service import CatalogoService

router = APIRouter(prefix="/api/v1", tags=["Catálogo"])

Servicio = Annotated[CatalogoService, Depends(get_catalogo_service)]
Lector = Annotated[Usuario, Depends(requiere(Permiso.CATALOGO_LEER))]
AdministradorCatalogo = Annotated[Usuario, Depends(requiere(Permiso.CATALOGO_ADMINISTRAR))]
LectorEjemplares = Annotated[Usuario, Depends(requiere(Permiso.EJEMPLAR_LEER))]
GestorEjemplares = Annotated[Usuario, Depends(requiere(Permiso.EJEMPLAR_ADMINISTRAR))]

_ERROR_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_ERROR_403 = {"description": "Sin permiso o ejemplar de otra sede (`FORBIDDEN`)"}
_ERROR_404_LIBRO = {"description": "El libro no existe (`LIBRO_NO_ENCONTRADO`)"}
_ERROR_404_EJEMPLAR = {"description": "El ejemplar no existe (`EJEMPLAR_NO_ENCONTRADO`)"}
_ERROR_422 = {"description": "Datos inválidos (`VALIDACION`, `CATEGORIA_INVALIDA`)"}


# --- categorías y libros -------------------------------------------------------------------------


@router.get(
    "/categorias",
    response_model=list[CategoriaResponse],
    summary="Categorías del catálogo",
    responses={401: _ERROR_401},
)
def listar_categorias(servicio: Servicio, actor: Lector) -> list[CategoriaResponse]:
    """Catálogo cerrado de categorías, ordenado por nombre."""
    return [CategoriaResponse.desde(c) for c in servicio.categorias(actor)]


@router.post(
    "/libros",
    response_model=LibroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de libro",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        409: {"description": "ISBN o título, autor, editorial y año repetidos (`LIBRO_DUPLICADO`)"},
        422: _ERROR_422,
    },
)
def crear_libro(
    datos: LibroRequest, response: Response, servicio: Servicio, actor: AdministradorCatalogo
) -> LibroResponse:
    """Agrega una obra al catálogo común de la red (solo el administrador)."""
    libro = servicio.crear_libro(actor, datos.a_datos())
    response.headers["Location"] = f"/api/v1/libros/{libro.id}"
    return libro_a_response(libro, actor)


@router.get(
    "/libros",
    response_model=PaginaLibrosResponse,
    summary="Búsqueda de libros",
    responses={401: _ERROR_401},
)
def buscar_libros(
    servicio: Servicio,
    actor: Lector,
    q: Annotated[str | None, Query(max_length=100, description="Título, autor o ISBN")] = None,
    categoria_id: int | None = None,
    tipo_material: TipoMaterial | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaLibrosResponse:
    """Busca por título, autor o ISBN (6 o más dígitos); cada libro trae sus ejemplares
    disponibles en la red. La auditoría solo la ve el administrador."""
    return PaginaLibrosResponse.desde(
        servicio.buscar_libros(actor, q, categoria_id, tipo_material, page, size), actor
    )


@router.get(
    "/libros/{libro_id}",
    response_model=LibroResponse,
    summary="Detalle de un libro",
    responses={401: _ERROR_401, 404: _ERROR_404_LIBRO},
)
def obtener_libro(libro_id: int, servicio: Servicio, actor: Lector) -> LibroResponse:
    """La auditoría y si se puede eliminar solo los ve el administrador."""
    return libro_a_response(servicio.obtener_libro(actor, libro_id), actor)


@router.put(
    "/libros/{libro_id}",
    response_model=LibroResponse,
    summary="Modificar un libro",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_LIBRO,
        409: {
            "description": "Coincide con otro libro (`LIBRO_DUPLICADO`) o `CONFLICTO_DE_VERSION`"
        },
        422: _ERROR_422,
    },
)
def modificar_libro(
    libro_id: int, datos: LibroModificarRequest, servicio: Servicio, actor: AdministradorCatalogo
) -> LibroResponse:
    libro = servicio.modificar_libro(actor, libro_id, datos.a_datos(), datos.version)
    return libro_a_response(libro, actor)


@router.delete(
    "/libros/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un libro sin ejemplares",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_LIBRO,
        409: {"description": "Tiene ejemplares (`LIBRO_CON_EJEMPLARES`)"},
    },
)
def eliminar_libro(libro_id: int, servicio: Servicio, actor: AdministradorCatalogo) -> Response:
    """Elimina un libro cargado por error. Un libro con ejemplares no se elimina."""
    servicio.eliminar_libro(actor, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/libros/{libro_id}/disponibilidad",
    response_model=DisponibilidadResponse,
    summary="Disponibilidad de un libro por sede",
    responses={401: _ERROR_401, 404: _ERROR_404_LIBRO},
)
def disponibilidad(libro_id: int, servicio: Servicio, actor: Lector) -> DisponibilidadResponse:
    """Por sede activa: ejemplares totales, disponibles, prestados, reservados y en tránsito."""
    return DisponibilidadResponse.desde(servicio.disponibilidad(actor, libro_id))


# --- ejemplares ----------------------------------------------------------------------------------


@router.post(
    "/ejemplares",
    response_model=EjemplarResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de ejemplar",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: {"description": "El libro o la sede no existen"},
        409: {"description": "Código repetido (`EJEMPLAR_CODIGO_DUPLICADO`) o `SEDE_EN_BAJA`"},
        422: _ERROR_422,
    },
)
def crear_ejemplar(
    datos: EjemplarCrearRequest, response: Response, servicio: Servicio, actor: GestorEjemplares
) -> EjemplarResponse:
    """Carga una copia física `DISPONIBLE` en la sede del bibliotecario (o la que indique el
    administrador)."""
    ejemplar = servicio.crear_ejemplar(actor, datos.a_datos())
    response.headers["Location"] = f"/api/v1/ejemplares/{ejemplar.id}"
    return EjemplarResponse.desde(ejemplar)


@router.get(
    "/ejemplares",
    response_model=PaginaEjemplaresResponse,
    summary="Listado de ejemplares",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def listar_ejemplares(
    servicio: Servicio,
    actor: LectorEjemplares,
    sede_id: int | None = None,
    libro_id: int | None = None,
    estado: EstadoEjemplarEnum | None = None,
    codigo: Annotated[str | None, Query(max_length=30)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaEjemplaresResponse:
    """Filtra por sede (propietaria o actual), libro, estado o código de inventario."""
    return PaginaEjemplaresResponse.desde(
        servicio.listar_ejemplares(actor, sede_id, libro_id, estado, codigo, page, size)
    )


@router.get(
    "/ejemplares/{ejemplar_id}",
    response_model=EjemplarDetalleResponse,
    summary="Detalle e historial de un ejemplar",
    responses={401: _ERROR_401, 403: _ERROR_403, 404: _ERROR_404_EJEMPLAR},
)
def obtener_ejemplar(
    ejemplar_id: int, servicio: Servicio, actor: LectorEjemplares
) -> EjemplarDetalleResponse:
    return EjemplarDetalleResponse.desde_detalle(servicio.detalle_ejemplar(actor, ejemplar_id))


@router.put(
    "/ejemplares/{ejemplar_id}",
    response_model=EjemplarResponse,
    summary="Modificar estado físico u observaciones",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_EJEMPLAR,
        409: {"description": "`CONFLICTO_DE_VERSION` o dado de baja (`TRANSICION_INVALIDA`)"},
        422: _ERROR_422,
    },
)
def modificar_ejemplar(
    ejemplar_id: int,
    datos: EjemplarModificarRequest,
    servicio: Servicio,
    actor: GestorEjemplares,
) -> EjemplarResponse:
    """La disponibilidad no se edita: la cambian préstamos, envíos, reservas y devoluciones.

    El cambio queda en el historial. Un ejemplar dado de baja no se edita."""
    return EjemplarResponse.desde(
        servicio.modificar_ejemplar(
            actor, ejemplar_id, datos.version, datos.estado_fisico, datos.observaciones
        )
    )


@router.post(
    "/ejemplares/{ejemplar_id}/baja",
    response_model=EjemplarResponse,
    summary="Baja lógica de un ejemplar",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_EJEMPLAR,
        409: {"description": "En uso (`EJEMPLAR_NO_DISPONIBLE`) o `CONFLICTO_DE_VERSION`"},
        422: _ERROR_422,
    },
)
def dar_de_baja_ejemplar(
    ejemplar_id: int, datos: EjemplarBajaRequest, servicio: Servicio, actor: GestorEjemplares
) -> EjemplarResponse:
    """Solo un ejemplar disponible o en revisión; queda en su historial."""
    return EjemplarResponse.desde(
        servicio.dar_de_baja_ejemplar(actor, ejemplar_id, datos.version, datos.motivo)
    )


@router.post(
    "/ejemplares/{ejemplar_id}/reparado",
    response_model=EjemplarResponse,
    summary="Marcar como reparado",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_EJEMPLAR,
        409: {"description": "No estaba en revisión (`TRANSICION_INVALIDA`)"},
    },
)
def reparar_ejemplar(
    ejemplar_id: int, datos: VersionRequest, servicio: Servicio, actor: GestorEjemplares
) -> EjemplarResponse:
    """Un ejemplar en revisión vuelve a estar disponible."""
    return EjemplarResponse.desde(servicio.reparar_ejemplar(actor, ejemplar_id, datos.version))


@router.post(
    "/ejemplares/{ejemplar_id}/recuperar",
    response_model=EjemplarResponse,
    summary="Recuperar un ejemplar extraviado",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404_EJEMPLAR,
        409: {
            "description": "No está dado de baja por un extravío (`EJEMPLAR_NO_RECUPERABLE`) "
            "o `CONFLICTO_DE_VERSION`"
        },
        422: _ERROR_422,
    },
)
def recuperar_ejemplar(
    ejemplar_id: int,
    datos: RecuperarEjemplarRequest,
    servicio: Servicio,
    actor: GestorEjemplares,
) -> EjemplarResponse:
    """Un ejemplar dado de baja por extravío apareció: vuelve a su sede propietaria.

    Queda disponible (o en revisión si llegó dañado) y la incidencia de extravío queda resuelta.
    Una baja por destrucción o daño irreparable es definitiva.
    """
    return EjemplarResponse.desde(
        servicio.recuperar_ejemplar(
            actor, ejemplar_id, datos.version, datos.estado_fisico, datos.observacion
        )
    )
