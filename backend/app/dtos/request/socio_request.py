"""Cuerpos de entrada de la API de socios. El formato de cada dato lo valida el dominio."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.socio import TipoDocumento
from app.services.socio_service import DatosSocio

_EJEMPLO_DATOS = {
    "tipo_documento": "DNI",
    "nro_documento": "30111222",
    "nombre": "Lucía",
    "apellido": "Gómez",
    "fecha_nacimiento": "1995-04-12",
    "email": "lucia@example.com",
    "telefono": "+543515000000",
    "domicilio": "San Martín 123",
}


class SocioDatosRequest(BaseModel):
    """Datos personales del socio (alta y modificación)."""

    model_config = ConfigDict(json_schema_extra={"example": _EJEMPLO_DATOS})

    tipo_documento: TipoDocumento
    nro_documento: str = Field(max_length=30)
    nombre: str = Field(max_length=300)
    apellido: str = Field(max_length=300)
    fecha_nacimiento: date | None = None
    email: str | None = Field(default=None, max_length=300)
    telefono: str | None = Field(default=None, max_length=40)
    domicilio: str | None = Field(default=None, max_length=400)

    def a_datos(self) -> DatosSocio:
        return DatosSocio(
            tipo_documento=self.tipo_documento,
            nro_documento=self.nro_documento,
            nombre=self.nombre,
            apellido=self.apellido,
            fecha_nacimiento=self.fecha_nacimiento,
            email=self.email,
            telefono=self.telefono,
            domicilio=self.domicilio,
        )


class SocioCrearRequest(SocioDatosRequest):
    """Alta de socio.

    ``sede_alta_id`` lo indica el administrador; para el bibliotecario es su sede.
    ``confirmar_posible_duplicado`` confirma que es otra persona cuando ya hay un socio con el
    mismo nombre y fecha de nacimiento.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {**_EJEMPLO_DATOS, "confirmar_posible_duplicado": False}}
    )

    sede_alta_id: int | None = None
    confirmar_posible_duplicado: bool = False


class MotivoRequest(BaseModel):
    """Motivo de una inhabilitación administrativa o de una baja."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"motivo": "Daño reiterado de material prestado"}}
    )

    motivo: str = Field(max_length=500)


class CuentaSocioRequest(BaseModel):
    """Usuario y contraseña con los que el socio va a ingresar."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "lucia.gomez", "password": "Clave-segura-123"}}
    )

    username: str = Field(max_length=100)
    password: str = Field(max_length=300)
