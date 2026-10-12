from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from biblioteca.application.services.sede_service import DatosSede, FranjaHoraria


class DatosSedeEntrada(BaseModel):
    nombre: str = Field(max_length=100)
    direccion: str = Field(max_length=200)
    localidad: str = Field(max_length=100)
    telefono: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=120)

    def a_datos(self) -> DatosSede:
        return DatosSede(
            nombre=self.nombre,
            direccion=self.direccion,
            localidad=self.localidad,
            telefono=self.telefono,
            email=self.email,
        )


class SedeCrear(DatosSedeEntrada):
    codigo: str = Field(min_length=2, max_length=5, examples=["CEN"])


class FranjaHorariaEntrada(BaseModel):
    dia_semana: int = Field(ge=1, le=7, description="1 = lunes ... 7 = domingo")
    hora_apertura: time = Field(examples=["08:00"])
    hora_cierre: time = Field(examples=["20:00"])

    def a_franja(self) -> FranjaHoraria:
        return FranjaHoraria(self.dia_semana, self.hora_apertura, self.hora_cierre)


class HorarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dia_semana: int
    hora_apertura: time
    hora_cierre: time


class SedeSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    direccion: str
    localidad: str
    telefono: str | None
    email: str | None
    activa: bool
    fecha_baja: datetime | None
    horarios: list[HorarioSalida]
