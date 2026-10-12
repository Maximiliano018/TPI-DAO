from datetime import datetime, time

from pydantic import BaseModel, Field

from biblioteca.application.services.sedes import DatosSede, FranjaHoraria


class HorarioOut(BaseModel):
    dia_semana: int
    hora_apertura: time
    hora_cierre: time


class SedeOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    direccion: str
    localidad: str
    telefono: str | None
    email: str | None
    activa: bool
    fecha_baja: datetime | None
    cantidad_ejemplares: int
    horarios: list[HorarioOut]


class DatosSedeIn(BaseModel):
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


class SedeIn(DatosSedeIn):
    codigo: str = Field(min_length=2, max_length=5, examples=["CEN"])


class HorarioIn(BaseModel):
    dia_semana: int = Field(ge=1, le=7, description="1 = lunes ... 7 = domingo")
    hora_apertura: time = Field(examples=["08:00"])
    hora_cierre: time = Field(examples=["20:00"])

    def a_franja(self) -> FranjaHoraria:
        return FranjaHoraria(self.dia_semana, self.hora_apertura, self.hora_cierre)


class SocioOut(BaseModel):
    id: int
    numero_socio: int
    dni: str
    nombre: str
    apellido: str
    email: str | None
    telefono: str | None
    habilitado: bool
    motivo_inhabilitacion: str | None
    activo: bool
    prestamos_abiertos: int
    multas_pendientes: int  # centavos
