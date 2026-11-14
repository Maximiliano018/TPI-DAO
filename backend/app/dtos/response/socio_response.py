"""Respuestas de la API de socios."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.paginacion import Pagina
from app.models.socio import SituacionSocio, Socio
from app.services.socio_service import BajaDeSocio, FichaSocio


class SocioResumenResponse(BaseModel):
    """Socio en un listado o en una búsqueda."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 45,
                "numero_socio": "00045",
                "tipo_documento": "DNI",
                "nro_documento": "30111222",
                "nombre": "Lucía",
                "apellido": "Gómez",
                "estado": "HABILITADO",
                "motivo_inhabilitacion": None,
                "sede_alta_id": 2,
                "sede_alta": "Sede Norte",
            }
        }
    )

    id: int
    numero_socio: str
    tipo_documento: str
    nro_documento: str
    nombre: str
    apellido: str
    estado: str
    motivo_inhabilitacion: str | None
    sede_alta_id: int
    sede_alta: str | None

    @classmethod
    def desde(cls, socio: Socio) -> "SocioResumenResponse":
        assert socio.id is not None
        motivo = socio.motivo_inhabilitacion
        return cls(
            id=socio.id,
            numero_socio=socio.numero_socio,
            tipo_documento=socio.datos.documento.tipo.value,
            nro_documento=socio.datos.documento.numero,
            nombre=socio.datos.nombre,
            apellido=socio.datos.apellido,
            estado=socio.estado.value,
            motivo_inhabilitacion=motivo.value if motivo else None,
            sede_alta_id=socio.sede_alta_id,
            sede_alta=socio.sede_alta_nombre,
        )


class CuentaResponse(BaseModel):
    usuario_id: int
    username: str
    activo: bool


class SituacionResponse(BaseModel):
    """Actividad del socio en la red."""

    prestamos_activos: int
    prestamos_vencidos: int
    multas_pendientes: int
    reservas_activas: int

    @classmethod
    def desde(cls, situacion: SituacionSocio) -> "SituacionResponse":
        return cls(
            prestamos_activos=situacion.prestamos_activos,
            prestamos_vencidos=situacion.prestamos_vencidos,
            multas_pendientes=situacion.multas_pendientes,
            reservas_activas=situacion.reservas_activas,
        )


class SocioResponse(SocioResumenResponse):
    """Datos completos del socio, su estado y su auditoría."""

    fecha_nacimiento: date | None
    email: str | None
    telefono: str | None
    domicilio: str | None
    causas_inhabilitacion: list[str]
    motivo_administrativo: str | None
    fecha_alta: datetime | None
    fecha_baja: datetime | None
    motivo_baja: str | None
    creado_por: UsuarioRefResponse | None
    actualizado_en: datetime | None
    actualizado_por: UsuarioRefResponse | None
    cuenta: CuentaResponse | None

    @classmethod
    def desde(cls, socio: Socio) -> "SocioResponse":
        datos = socio.datos
        resumen = SocioResumenResponse.desde(socio).model_dump()
        return cls(
            **resumen,
            fecha_nacimiento=datos.fecha_nacimiento,
            email=datos.email.valor if datos.email else None,
            telefono=datos.telefono.valor if datos.telefono else None,
            domicilio=datos.domicilio,
            causas_inhabilitacion=sorted(c.value for c in socio.causas),
            motivo_administrativo=socio.motivo_administrativo,
            fecha_alta=socio.fecha_alta,
            fecha_baja=socio.fecha_baja,
            motivo_baja=socio.motivo_baja,
            creado_por=UsuarioRefResponse.desde(socio.creado_por) if socio.creado_por else None,
            actualizado_en=socio.actualizado_en,
            actualizado_por=(
                UsuarioRefResponse.desde(socio.actualizado_por) if socio.actualizado_por else None
            ),
            cuenta=(
                CuentaResponse(
                    usuario_id=socio.cuenta.usuario_id,
                    username=socio.cuenta.username,
                    activo=socio.cuenta.activo,
                )
                if socio.cuenta
                else None
            ),
        )


class FichaSocioResponse(SocioResponse):
    """Socio con su situación: préstamos, multas y reservas (RF-SOC-10)."""

    situacion: SituacionResponse

    @classmethod
    def desde_ficha(cls, ficha: FichaSocio) -> "FichaSocioResponse":
        return cls(
            **SocioResponse.desde(ficha.socio).model_dump(),
            situacion=SituacionResponse.desde(ficha.situacion),
        )


class BajaSocioResponse(SocioResponse):
    """Socio dado de baja y cuántas reservas activas se le cancelaron (CU-SOC-04, A2)."""

    reservas_canceladas: int

    @classmethod
    def desde_baja(cls, baja: BajaDeSocio) -> "BajaSocioResponse":
        return cls(
            **SocioResponse.desde(baja.socio).model_dump(),
            reservas_canceladas=baja.reservas_canceladas,
        )


class PaginaSociosResponse(BaseModel):
    items: list[SocioResumenResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Socio]) -> "PaginaSociosResponse":
        return cls(
            items=[SocioResumenResponse.desde(s) for s in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
