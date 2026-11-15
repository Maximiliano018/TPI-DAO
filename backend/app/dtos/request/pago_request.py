"""Cuerpos de entrada del pago de multas."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.pago import FormaEnLinea, MedioPago


class SaldarMultaRequest(BaseModel):
    """Cobro en el mostrador: ``medio`` es efectivo, débito, crédito o transferencia."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"medio": "DEBITO", "comprobante": "Cupón 004512"}}
    )

    medio: MedioPago
    comprobante: str | None = Field(default=None, max_length=100)


class PagoEnLineaRequest(BaseModel):
    """Confirmación del checkout simulado. De la tarjeta solo viajan sus últimos 4 dígitos: el
    número completo, el vencimiento y el código de seguridad nunca salen del navegador."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"forma": "TARJETA_CREDITO", "tarjeta_ultimos4": "3704"}}
    )

    forma: FormaEnLinea
    tarjeta_ultimos4: str | None = Field(default=None, min_length=4, max_length=4)
