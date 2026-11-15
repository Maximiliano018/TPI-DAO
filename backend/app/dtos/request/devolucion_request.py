"""Cuerpos de entrada de devoluciones."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.devolucion import EstadoRecibido


class DevolucionRequest(BaseModel):
    """Sin ``fecha_hora`` se toma el momento actual. Una fecha anterior a hoy (el socio lo
    devolvió antes y se registra ahora) exige ``motivo_fecha``: cambia el atraso y la multa."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"estado_fisico": "BUENO", "observaciones": "Sin novedades"}}
    )

    estado_fisico: EstadoRecibido
    observaciones: str | None = Field(default=None, max_length=300)
    fecha_hora: datetime | None = None
    motivo_fecha: str | None = Field(default=None, max_length=300)
