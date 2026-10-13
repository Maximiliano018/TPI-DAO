from datetime import datetime

from pydantic import BaseModel

from biblioteca.domain.enums import EstadoRemito, ResultadoRevision, Sentido


class RemitoOut(BaseModel):
    id: int
    numero: str
    sentido: Sentido
    estado: EstadoRemito
    prestamo_id: int | None
    socio: str | None
    codigo_inventario: str
    titulo: str
    sede_origen_id: int
    sede_origen: str
    sede_destino_id: int
    sede_destino: str
    fecha_generacion: datetime
    fecha_despacho: datetime | None
    fecha_recepcion: datetime | None
    resultado_revision: ResultadoRevision | None
    observacion_revision: str | None
    dias_en_transito: int | None
    demorado: bool


class MovimientoRemitoOut(BaseModel):
    id: int
    estado_anterior: EstadoRemito | None
    estado_nuevo: EstadoRemito
    fecha_hora: datetime
    usuario: str
    observacion: str | None
