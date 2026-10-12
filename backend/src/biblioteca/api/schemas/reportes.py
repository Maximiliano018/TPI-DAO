"""DTOs del tablero y de los reportes. Los importes van en centavos."""

from datetime import date, datetime

from pydantic import BaseModel

from biblioteca.domain.enums import EstadoRemito

# ------------------------------------------------------------------------ Tablero (R6)


class VencimientoOut(BaseModel):
    id: int
    socio: str
    titulo: str
    sede: str
    fecha_vencimiento: date
    dias_restantes: int


class UltimoMovimientoOut(BaseModel):
    id: int
    remito_id: int
    numero: str
    titulo: str
    estado_nuevo: EstadoRemito
    fecha_hora: datetime
    usuario: str


class TableroOut(BaseModel):
    prestamos_activos: int
    prestamos_vencidos: int
    prestamos_en_envio: int
    listos_para_retiro: int
    remitos_en_transito: int
    remitos_demorados: int
    reservas_pendientes: int
    reservas_asignadas: int
    multas_pendientes: int
    multas_pendientes_monto: int
    proximos_vencimientos: list[VencimientoOut]
    ultimos_movimientos: list[UltimoMovimientoOut]


# --------------------------------------------------------------- R1 · Movimiento entre sedes


class RutaOut(BaseModel):
    sede_origen_id: int
    sede_origen: str
    sede_destino_id: int
    sede_destino: str
    envios: int
    recibidos: int
    en_curso: int
    extraviados: int
    dias_promedio_transito: float | None


class MovimientoSedesOut(BaseModel):
    envios_totales: int
    dias_promedio_transito: float | None
    rutas: list[RutaOut]


# ------------------------------------------------------------------- R2 · Envíos exitosos


class IncidenciasOut(BaseModel):
    danados: int
    destruidos: int
    extraviados: int


class EnviosSedeOut(BaseModel):
    sede_id: int
    sede: str
    total: int
    exitosos: int
    danados: int
    destruidos: int
    extraviados: int
    incidencias: int
    tasa_exito: float | None


class EnviosExitososOut(BaseModel):
    total: int
    exitosos: int
    tasa_exito: float | None
    incidencias: IncidenciasOut
    por_sede: list[EnviosSedeOut]


# ------------------------------------------------------------ R3 · Libros más solicitados


class LibroSolicitadoOut(BaseModel):
    libro_id: int
    titulo: str
    isbn: str
    solicitudes: int
    socios: int
    sedes_destino: int


# ------------------------------------------------------------ R4 · Vencidos y multas


class PrestamoVencidoOut(BaseModel):
    id: int
    socio: str
    numero_socio: int
    titulo: str
    codigo_inventario: str
    sede: str
    fecha_inicio: date
    fecha_vencimiento: date
    dias_atraso: int


class MultasSocioOut(BaseModel):
    socio_id: int
    socio: str
    cantidad: int
    pendiente: int
    saldado: int


class MultasSedeOut(BaseModel):
    sede_id: int
    sede: str
    cantidad: int
    pendiente: int
    saldado: int


class VencidosMultasOut(BaseModel):
    vencidos: list[PrestamoVencidoOut]
    multas_por_socio: list[MultasSocioOut]
    multas_por_sede: list[MultasSedeOut]
    total_pendiente: int
    total_saldado: int
