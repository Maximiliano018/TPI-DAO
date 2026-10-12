from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from biblioteca.domain.enums import (
    CondicionFisica,
    EstadoMulta,
    EstadoPrestamo,
    EstadoReserva,
    MotivoCancelacion,
)


class PrestamoOut(BaseModel):
    id: int
    tipo: Literal["LOCAL", "INTERSEDES"]
    estado: EstadoPrestamo
    socio_id: int
    socio: str
    numero_socio: int
    titulo: str
    codigo_inventario: str
    sede_origen_id: int
    sede_origen: str
    sede_destino_id: int
    sede_destino: str
    fecha_solicitud: datetime
    fecha_limite_retiro: date | None
    fecha_inicio: date | None
    fecha_vencimiento: date | None
    fecha_cierre: datetime | None
    motivo_cancelacion: MotivoCancelacion | None
    vencido: bool
    dias_atraso: int
    retiro_vencido: bool


class ReservaOut(BaseModel):
    id: int
    estado: EstadoReserva
    socio: str
    libro_id: int
    titulo: str
    sede_id: int
    sede: str
    fecha_solicitud: datetime
    fecha_asignacion: datetime | None
    fecha_limite: date | None
    fecha_cierre: datetime | None
    ejemplar_asignado: str | None
    posicion_cola: int | None


class DevolucionOut(BaseModel):
    id: int
    fecha_hora: datetime
    condicion_fisica: CondicionFisica
    observacion: str | None
    prestamo_id: int
    fecha_vencimiento: date | None
    socio: str
    titulo: str
    codigo_inventario: str
    sede: str
    registrado_por: str
    dias_atraso: int | None
    multa_monto: int | None  # centavos
    multa_estado: EstadoMulta | None
