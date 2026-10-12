from datetime import time

from pydantic import BaseModel


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
    cantidad_ejemplares: int
    horarios: list[HorarioOut]


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
