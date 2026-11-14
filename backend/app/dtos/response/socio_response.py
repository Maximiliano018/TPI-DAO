"""Respuestas de la API de socios.

Hay un esquema por rol, como en sedes: los campos que el usuario no puede ver no existen en su
esquema, así que no se serializan (ni siquiera como ``null``).

- **Socio** (``SocioPropioResponse``, solo el propio): sus datos, estado, causas y motivos, baja,
  solicitud de reactivación, situación y el nombre de usuario de su cuenta.
- **Bibliotecario** (``SocioPersonalResponse``): agrega la sede de alta y la cuenta completa.
- **Administrador** (``SocioAdminResponse``): agrega la auditoría (quién lo creó y lo modificó).
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.paginacion import Pagina
from app.models.sede import Cambio
from app.models.socio import EventoSocio, SituacionSocio, Socio
from app.models.usuario import Permiso, Usuario

AUTOR_SISTEMA = "Sistema"
AUTOR_PERSONAL = "Personal de la biblioteca"
AUTOR_PROPIO = "Vos"


class SocioResumenResponse(BaseModel):
    """Socio en un listado o en una búsqueda (solo personal)."""

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
                "tipo_baja": None,
                "solicitud_pendiente": False,
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
    tipo_baja: str | None
    solicitud_pendiente: bool
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
            tipo_baja=socio.tipo_baja.value if socio.tipo_baja else None,
            solicitud_pendiente=socio.solicitud is not None,
            sede_alta_id=socio.sede_alta_id,
            sede_alta=socio.sede_alta_nombre,
        )


class CuentaPropiaResponse(BaseModel):
    """Lo que el socio ve de su cuenta."""

    username: str


class CuentaResponse(CuentaPropiaResponse):
    """Lo que el personal ve de la cuenta del socio."""

    usuario_id: int
    activo: bool


class SolicitudResponse(BaseModel):
    """Solicitud de reactivación pendiente."""

    fecha: datetime
    mensaje: str | None


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


class SocioPropioResponse(BaseModel):
    """Lo que ve el socio de sí mismo.

    ``situacion`` viene en la ficha; ``reservas_canceladas``, en la respuesta de la baja.
    """

    id: int
    numero_socio: str
    tipo_documento: str
    nro_documento: str
    nombre: str
    apellido: str
    fecha_nacimiento: date | None
    email: str | None
    telefono: str | None
    domicilio: str | None
    estado: str
    motivo_inhabilitacion: str | None
    causas_inhabilitacion: list[str]
    motivo_administrativo: str | None
    sede_alta: str | None
    fecha_alta: datetime | None
    tipo_baja: str | None
    fecha_baja: datetime | None
    motivo_baja: str | None
    reactivable: bool
    solicitud: SolicitudResponse | None
    cuenta: CuentaPropiaResponse | None
    situacion: SituacionResponse | None = None
    reservas_canceladas: int | None = None


class SocioPersonalResponse(SocioPropioResponse):
    """Lo que ve el bibliotecario: agrega la sede de alta y la cuenta completa."""

    sede_alta_id: int
    cuenta: CuentaResponse | None


class SocioAdminResponse(SocioPersonalResponse):
    """Lo que ve el administrador: agrega la auditoría."""

    creado_por: UsuarioRefResponse | None
    actualizado_en: datetime | None
    actualizado_por: UsuarioRefResponse | None


SocioResponse = SocioAdminResponse | SocioPersonalResponse | SocioPropioResponse


def socio_a_response(
    socio: Socio,
    usuario: Usuario,
    *,
    situacion: SituacionSocio | None = None,
    reservas_canceladas: int | None = None,
) -> SocioResponse:
    """Arma el esquema que corresponde al rol del usuario."""
    assert socio.id is not None
    datos = socio.datos
    motivo = socio.motivo_inhabilitacion
    campos: dict[str, Any] = {
        "id": socio.id,
        "numero_socio": socio.numero_socio,
        "tipo_documento": datos.documento.tipo.value,
        "nro_documento": datos.documento.numero,
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "fecha_nacimiento": datos.fecha_nacimiento,
        "email": datos.email.valor if datos.email else None,
        "telefono": datos.telefono.valor if datos.telefono else None,
        "domicilio": datos.domicilio,
        "estado": socio.estado.value,
        "motivo_inhabilitacion": motivo.value if motivo else None,
        "causas_inhabilitacion": sorted(c.value for c in socio.causas),
        "motivo_administrativo": socio.motivo_administrativo,
        "sede_alta": socio.sede_alta_nombre,
        "fecha_alta": socio.fecha_alta,
        "tipo_baja": socio.tipo_baja.value if socio.tipo_baja else None,
        "fecha_baja": socio.fecha_baja,
        "motivo_baja": socio.motivo_baja,
        "reactivable": socio.reactivable,
        "solicitud": (
            SolicitudResponse(fecha=socio.solicitud.fecha, mensaje=socio.solicitud.mensaje)
            if socio.solicitud
            else None
        ),
        "situacion": SituacionResponse.desde(situacion) if situacion else None,
        "reservas_canceladas": reservas_canceladas,
    }
    cuenta = socio.cuenta
    if not usuario.puede(Permiso.SOCIO_LEER):
        return SocioPropioResponse(
            **campos, cuenta=CuentaPropiaResponse(username=cuenta.username) if cuenta else None
        )
    campos["sede_alta_id"] = socio.sede_alta_id
    campos["cuenta"] = (
        CuentaResponse(usuario_id=cuenta.usuario_id, username=cuenta.username, activo=cuenta.activo)
        if cuenta
        else None
    )
    if not usuario.puede(Permiso.SOCIO_ADMINISTRAR):
        return SocioPersonalResponse(**campos)
    return SocioAdminResponse(
        **campos,
        creado_por=UsuarioRefResponse.desde(socio.creado_por) if socio.creado_por else None,
        actualizado_en=socio.actualizado_en,
        actualizado_por=(
            UsuarioRefResponse.desde(socio.actualizado_por) if socio.actualizado_por else None
        ),
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


class CambioResponse(BaseModel):
    campo: str
    antes: Any
    despues: Any

    @classmethod
    def desde(cls, cambio: Cambio) -> "CambioResponse":
        return cls(campo=cambio.campo, antes=cambio.antes, despues=cambio.despues)


class EventoSocioResponse(BaseModel):
    """Evento del historial del socio.

    ``autor`` es el nombre para mostrar. El personal ve quién fue (``usuario``); el socio ve
    «Vos», «Personal de la biblioteca» o «Sistema», y ``usuario`` llega siempre nulo.
    """

    id: int
    tipo_evento: str
    fecha_hora: datetime
    autor: str
    usuario: UsuarioRefResponse | None
    estado_anterior: str | None
    estado_nuevo: str | None
    motivo: str | None
    origen: str | None
    cambios: list[CambioResponse]

    @classmethod
    def desde(cls, evento: EventoSocio, lector: Usuario) -> "EventoSocioResponse":
        assert evento.id is not None
        personal = lector.puede(Permiso.SOCIO_LEER)
        if evento.usuario is None:
            autor = AUTOR_SISTEMA
        elif personal:
            autor = evento.usuario.nombre
        else:
            autor = AUTOR_PROPIO if evento.usuario.id == lector.id else AUTOR_PERSONAL
        return cls(
            id=evento.id,
            tipo_evento=evento.tipo.value,
            fecha_hora=evento.fecha_hora,
            autor=autor,
            usuario=UsuarioRefResponse.desde(evento.usuario)
            if personal and evento.usuario
            else None,
            estado_anterior=evento.estado_anterior.value if evento.estado_anterior else None,
            estado_nuevo=evento.estado_nuevo.value if evento.estado_nuevo else None,
            motivo=evento.motivo,
            origen=evento.origen,
            cambios=[CambioResponse.desde(c) for c in evento.cambios],
        )


class PaginaHistorialSocioResponse(BaseModel):
    items: list[EventoSocioResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[EventoSocio], lector: Usuario) -> "PaginaHistorialSocioResponse":
        return cls(
            items=[EventoSocioResponse.desde(e, lector) for e in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
