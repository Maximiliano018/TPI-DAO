"""Respuestas de la API de sedes.

Hay un esquema por nivel de lectura: los campos que el usuario no puede ver directamente no
existen en su esquema, de modo que no se serializan (ni siquiera como ``null``).
"""

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel

from app.models.horario import ExcepcionHorario
from app.models.paginacion import Pagina
from app.models.sede import EventoSede, Sede, UsuarioRef
from app.models.usuario import Permiso, Usuario
from app.models.valores import Localidad
from app.services.sede_service import VistaSede


def _hora(valor: time | None) -> str | None:
    return valor.strftime("%H:%M") if valor else None


class UsuarioRefResponse(BaseModel):
    id: int
    nombre: str

    @classmethod
    def desde(cls, ref: UsuarioRef) -> "UsuarioRefResponse":
        return cls(id=ref.id, nombre=ref.nombre)


class DireccionResponse(BaseModel):
    calle: str
    numero: str
    localidad_id: int
    localidad: str
    provincia: str


class ContactoBasicoResponse(BaseModel):
    telefono: str
    email: str


class ContactoCompletoResponse(ContactoBasicoResponse):
    responsable: str


class FranjaResponse(BaseModel):
    dia_semana: int
    apertura: str
    cierre: str


class ExcepcionHorarioResponse(BaseModel):
    id: int
    fecha: date
    tipo: str
    hora_desde: str | None
    hora_hasta: str | None
    motivo: str | None

    @classmethod
    def desde(cls, excepcion: ExcepcionHorario) -> "ExcepcionHorarioResponse":
        assert excepcion.id is not None
        return cls(
            id=excepcion.id,
            fecha=excepcion.fecha,
            tipo=excepcion.tipo.value,
            hora_desde=_hora(excepcion.desde),
            hora_hasta=_hora(excepcion.hasta),
            motivo=excepcion.motivo,
        )


class BajaResponse(BaseModel):
    fecha: datetime
    motivo: str
    usuario: UsuarioRefResponse


class SedePublicaResponse(BaseModel):
    """Lo que ve un socio: datos de atención, sin responsable ni estado."""

    id: int
    codigo: str
    nombre: str
    direccion: DireccionResponse
    contacto: ContactoBasicoResponse
    horarios: list[FranjaResponse]
    excepciones: list[ExcepcionHorarioResponse]
    abierta_ahora: bool


class SedeBasicaResponse(BaseModel):
    """Lo que ve un bibliotecario: agrega el estado y el responsable."""

    id: int
    codigo: str
    nombre: str
    estado: str
    direccion: DireccionResponse
    contacto: ContactoCompletoResponse
    horarios: list[FranjaResponse]
    excepciones: list[ExcepcionHorarioResponse]
    abierta_ahora: bool


class SedeAdminResponse(SedeBasicaResponse):
    """Lo que ve un administrador: agrega la baja, la versión y la auditoría."""

    baja: BajaResponse | None
    version: int
    creado_en: datetime
    creado_por: UsuarioRefResponse
    actualizado_en: datetime
    actualizado_por: UsuarioRefResponse


SedeResponse = SedeAdminResponse | SedeBasicaResponse | SedePublicaResponse


def _campos_publicos(sede: Sede, vista: VistaSede) -> dict[str, Any]:
    localidad = sede.direccion.localidad
    return {
        "id": sede.id,
        "codigo": sede.codigo.valor,
        "nombre": sede.nombre,
        "direccion": DireccionResponse(
            calle=sede.direccion.calle,
            numero=sede.direccion.numero,
            localidad_id=localidad.id,
            localidad=localidad.nombre,
            provincia=localidad.provincia,
        ),
        "horarios": [
            FranjaResponse(
                dia_semana=f.dia, apertura=_hora(f.apertura) or "", cierre=_hora(f.cierre) or ""
            )
            for f in sede.horarios
        ],
        "excepciones": [
            ExcepcionHorarioResponse.desde(e) for e in sede.excepciones_vigentes(vista.hoy)
        ],
        "abierta_ahora": vista.abierta_ahora,
    }


def sede_a_response(vista: VistaSede, usuario: Usuario) -> SedeResponse:
    """Arma el esquema que corresponde al nivel de lectura del usuario."""
    sede = vista.sede
    campos = _campos_publicos(sede, vista)
    contacto = sede.contacto
    if not usuario.puede(Permiso.SEDE_LEER_BASICO):
        return SedePublicaResponse(
            **campos,
            contacto=ContactoBasicoResponse(
                telefono=contacto.telefono.valor, email=contacto.email.valor
            ),
        )
    completo = ContactoCompletoResponse(
        telefono=contacto.telefono.valor,
        email=contacto.email.valor,
        responsable=contacto.responsable,
    )
    if not usuario.puede(Permiso.SEDE_LEER_COMPLETO):
        return SedeBasicaResponse(**campos, estado=sede.estado.value, contacto=completo)
    baja = (
        BajaResponse(
            fecha=sede.baja.fecha,
            motivo=sede.baja.motivo,
            usuario=UsuarioRefResponse.desde(sede.baja.usuario),
        )
        if sede.baja
        else None
    )
    return SedeAdminResponse(
        **campos,
        estado=sede.estado.value,
        contacto=completo,
        baja=baja,
        version=sede.version,
        creado_en=sede.creado_en,
        creado_por=UsuarioRefResponse.desde(sede.creado_por),
        actualizado_en=sede.actualizado_en,
        actualizado_por=UsuarioRefResponse.desde(sede.actualizado_por),
    )


class PaginaSedesResponse(BaseModel):
    items: list[SedeAdminResponse | SedeBasicaResponse | SedePublicaResponse]
    total: int
    page: int
    size: int


def pagina_de_sedes(pagina: Pagina[VistaSede], usuario: Usuario) -> PaginaSedesResponse:
    return PaginaSedesResponse(
        items=[sede_a_response(v, usuario) for v in pagina.items],
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
    )


class SedesResumenResponse(BaseModel):
    total: int
    activas: int
    en_baja: int


class CambioResponse(BaseModel):
    campo: str
    antes: Any
    despues: Any


class EventoSedeResponse(BaseModel):
    id: int
    tipo_evento: str
    fecha_hora: datetime
    usuario: UsuarioRefResponse
    estado_anterior: str | None
    estado_nuevo: str | None
    motivo: str | None
    version_resultante: int
    cambios: list[CambioResponse]

    @classmethod
    def desde(cls, evento: EventoSede) -> "EventoSedeResponse":
        assert evento.id is not None
        return cls(
            id=evento.id,
            tipo_evento=evento.tipo.value,
            fecha_hora=evento.fecha_hora,
            usuario=UsuarioRefResponse.desde(evento.usuario),
            estado_anterior=evento.estado_anterior.value if evento.estado_anterior else None,
            estado_nuevo=evento.estado_nuevo.value if evento.estado_nuevo else None,
            motivo=evento.motivo,
            version_resultante=evento.version_resultante,
            cambios=[
                CambioResponse(campo=c.campo, antes=c.antes, despues=c.despues)
                for c in evento.cambios
            ],
        )


class PaginaHistorialResponse(BaseModel):
    items: list[EventoSedeResponse]
    total: int
    page: int
    size: int


class LocalidadResponse(BaseModel):
    id: int
    nombre: str
    departamento: str
    provincia_id: int
    provincia: str

    @classmethod
    def desde(cls, localidad: Localidad) -> "LocalidadResponse":
        return cls(
            id=localidad.id,
            nombre=localidad.nombre,
            departamento=localidad.departamento,
            provincia_id=localidad.provincia_id,
            provincia=localidad.provincia,
        )


class ProvinciaResponse(BaseModel):
    id: int
    nombre: str
