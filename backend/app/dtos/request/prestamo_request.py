"""Cuerpos de entrada de préstamos, remitos y parámetros."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.ejemplar import EstadoFisico
from app.models.remito import MotivoRemito, RecepcionLinea
from app.services.remito_service import LineaNueva


class PrestamoCrearRequest(BaseModel):
    """Préstamo registrado en mostrador. El tipo (local o entre sedes) se deduce de las sedes.

    ``sede_destino_id`` es la sede del bibliotecario (puede omitirse); el origen es la sede
    donde está el ejemplar.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"socio_id": 45, "ejemplar_id": 301, "sede_destino_id": 2}}
    )

    socio_id: int
    ejemplar_id: int
    sede_destino_id: int | None = None


class SolicitudPrestamoRequest(BaseModel):
    """El socio pide un libro para sí: el sistema elige el tipo y el ejemplar.

    ``sede_destino_id``: dónde lo retira (por defecto, su sede de alta). ``socio_id`` es
    opcional y, si viene, tiene que ser el propio. ``sede_origen_esperada_id`` es la sede de la
    propuesta que vio: si cambió, se rechaza con la nueva.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"libro_id": 12, "sede_destino_id": 2, "sede_origen_esperada_id": 1}
        }
    )

    libro_id: int
    sede_destino_id: int | None = None
    socio_id: int | None = None
    sede_origen_esperada_id: int | None = None


class CancelarRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"motivo": "El socio no lo retiró"}})

    motivo: str | None = Field(default=None, max_length=300)


class LineaRemitoRequest(BaseModel):
    ejemplar_id: int
    prestamo_id: int | None = None


class RemitoCrearRequest(BaseModel):
    """Remito desde la sede del bibliotecario: ``ENVIO`` (préstamos) o ``TRASLADO``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sede_destino_id": 2,
                "motivo": "ENVIO",
                "lineas": [{"ejemplar_id": 301, "prestamo_id": 118}],
            }
        }
    )

    sede_destino_id: int
    motivo: MotivoRemito
    lineas: list[LineaRemitoRequest] = Field(min_length=1, max_length=50)
    observaciones: str | None = Field(default=None, max_length=600)

    def a_lineas(self) -> list[LineaNueva]:
        return [LineaNueva(linea.ejemplar_id, linea.prestamo_id) for linea in self.lineas]


class LineaRecepcionRequest(BaseModel):
    ejemplar_id: int
    estado_fisico: EstadoFisico
    destruido: bool = False
    observacion: str | None = Field(default=None, max_length=600)


class RecepcionRequest(BaseModel):
    """Verificación de cada ejemplar al recibir (daño o destrucción con observación)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lineas": [
                    {"ejemplar_id": 301, "estado_fisico": "BUENO"},
                    {"ejemplar_id": 305, "estado_fisico": "DANADO", "observacion": "Tapa rota"},
                ]
            }
        }
    )

    lineas: list[LineaRecepcionRequest] = Field(min_length=1, max_length=50)

    def a_recepcion(self) -> list[RecepcionLinea]:
        return [
            RecepcionLinea(
                linea.ejemplar_id, linea.estado_fisico, linea.destruido, linea.observacion
            )
            for linea in self.lineas
        ]


class MotivoTextoRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"motivo": "El socio desistió del pedido"}}
    )

    motivo: str = Field(max_length=500)


class ParametroRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"valor": "21"}})

    valor: str = Field(max_length=40)
