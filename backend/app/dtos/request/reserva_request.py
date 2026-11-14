"""Cuerpos de entrada de reservas."""

from pydantic import BaseModel, ConfigDict, Field


class ReservaRequest(BaseModel):
    """El socio omite ``socio_id`` (se toma de su sesión; otro se rechaza); el bibliotecario lo
    indica."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"libro_id": 12, "sede_retiro_id": 2, "socio_id": 45}}
    )

    libro_id: int
    sede_retiro_id: int
    socio_id: int | None = None


class CancelarReservaRequest(BaseModel):
    """Motivo opcional: queda en el historial de la reserva."""

    model_config = ConfigDict(json_schema_extra={"example": {"motivo": "Ya lo conseguí"}})

    motivo: str | None = Field(default=None, max_length=300)
