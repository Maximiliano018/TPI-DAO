"""Cuerpos de entrada de la API de sedes.

Solo describen la forma; los formatos de negocio (código, teléfono, correo, horarios) los valida
el dominio para que todos los errores salgan con el mismo código y detalle.
"""

from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field

from app.models.horario import TipoExcepcion
from app.models.valores import FranjaHoraria
from app.services.sede_service import DatosExcepcion, DatosSede


class FranjaRequest(BaseModel):
    """Franja de atención de un día (1 = lunes ... 7 = domingo)."""

    dia_semana: int
    apertura: time
    cierre: time

    def a_dominio(self) -> FranjaHoraria:
        return FranjaHoraria(self.dia_semana, self.apertura, self.cierre)


class DatosSedeRequest(BaseModel):
    """Datos editables de una sede (alta y modificación)."""

    nombre: str = Field(max_length=200)
    calle: str = Field(max_length=200)
    numero: str = Field(max_length=20)
    localidad_id: int
    telefono: str = Field(max_length=40)
    email: str = Field(max_length=200)
    responsable: str = Field(max_length=200)
    horarios: list[FranjaRequest] = Field(max_length=28)
    confirmar_direccion_duplicada: bool = False

    def a_datos(self) -> DatosSede:
        return DatosSede(
            nombre=self.nombre,
            calle=self.calle,
            numero=self.numero,
            localidad_id=self.localidad_id,
            telefono=self.telefono,
            email=self.email,
            responsable=self.responsable,
            horarios=[h.a_dominio() for h in self.horarios],
        )


class SedeCrearRequest(DatosSedeRequest):
    """Alta de sede."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo": "norte",
                "nombre": "Sede Norte",
                "calle": "Av. Colón",
                "numero": "4500",
                "localidad_id": 1,
                "telefono": "+54 351 400-0000",
                "email": "Norte@red.example",
                "responsable": "Ana Pérez",
                "horarios": [
                    {"dia_semana": 1, "apertura": "09:00", "cierre": "13:00"},
                    {"dia_semana": 1, "apertura": "15:00", "cierre": "19:00"},
                ],
                "confirmar_direccion_duplicada": False,
            }
        }
    )

    codigo: str = Field(max_length=40)


class SedeModificarRequest(DatosSedeRequest):
    """Modificación completa; el ``codigo`` es opcional y, si se envía, debe ser el actual."""

    version: int
    codigo: str | None = Field(default=None, max_length=40)


class SedeBajaRequest(BaseModel):
    """Baja con motivo (5 a 300 caracteres)."""

    motivo: str = Field(max_length=2000)
    version: int


class SedeReactivarRequest(BaseModel):
    """Reactivación; exige la versión leída."""

    version: int


class ExcepcionHorarioRequest(BaseModel):
    """Cierre por fecha o rango de fechas (máximo 31 días)."""

    fecha_desde: date
    fecha_hasta: date | None = None
    tipo: TipoExcepcion
    hora_desde: time | None = None
    hora_hasta: time | None = None
    motivo: str | None = Field(default=None, max_length=1000)

    def a_datos(self) -> DatosExcepcion:
        return DatosExcepcion(
            fecha_desde=self.fecha_desde,
            fecha_hasta=self.fecha_hasta,
            tipo=self.tipo,
            hora_desde=self.hora_desde,
            hora_hasta=self.hora_hasta,
            motivo=self.motivo,
        )
