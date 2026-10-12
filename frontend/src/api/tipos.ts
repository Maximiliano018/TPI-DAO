// Espejo de los DTOs del backend (backend/src/biblioteca/api/schemas). Importes en centavos.

export type EstadoEjemplar =
  | 'DISPONIBLE'
  | 'RESERVADO'
  | 'PENDIENTE_DESPACHO'
  | 'EN_TRANSITO'
  | 'PRESTADO'
  | 'EN_REVISION'
  | 'BAJA'
export type CondicionFisica = 'BUENA' | 'REGULAR' | 'DANADA'
export type EstadoPrestamo = 'EN_ENVIO' | 'LISTO_PARA_RETIRO' | 'ACTIVO' | 'DEVUELTO' | 'CANCELADO'
export type EstadoReserva = 'PENDIENTE' | 'ASIGNADA' | 'CUMPLIDA' | 'CANCELADA' | 'VENCIDA'
export type EstadoRemito =
  | 'GENERADO'
  | 'EMPAQUETADO'
  | 'EN_TRANSITO'
  | 'RECIBIDO'
  | 'EXTRAVIADO'
  | 'CANCELADO'
export type ResultadoRevision = 'CONFORME' | 'DANADO' | 'DESTRUIDO'
export type EstadoMulta = 'PENDIENTE' | 'SALDADA'

export type Sede = {
  id: number
  codigo: string
  nombre: string
  direccion: string
  localidad: string
  telefono: string | null
  email: string | null
  activa: boolean
  cantidad_ejemplares: number
  horarios: { dia_semana: number; hora_apertura: string; hora_cierre: string }[]
}

export type Socio = {
  id: number
  numero_socio: number
  dni: string
  nombre: string
  apellido: string
  email: string | null
  telefono: string | null
  habilitado: boolean
  motivo_inhabilitacion: string | null
  activo: boolean
  prestamos_abiertos: number
  multas_pendientes: number
}

export type Libro = {
  id: number
  isbn: string
  titulo: string
  editorial: string | null
  anio_publicacion: number | null
  categoria: string | null
  autores: string[]
  ejemplares: number
  disponibles: number
}

export type NuevoLibro = {
  isbn: string
  titulo: string
  autores: string[]
  editorial: string | null
  anio_publicacion: number | null
  categoria_id: number | null
}

export type Categoria = { id: number; nombre: string }

export type Ejemplar = {
  id: number
  codigo_inventario: string
  libro_id: number
  titulo: string
  sede_id: number
  sede: string
  estado: EstadoEjemplar
  condicion_fisica: CondicionFisica
  prestable: boolean
  fecha_alta: string
  motivo_baja: string | null
}

export type DisponibilidadSede = {
  sede_id: number
  sede: string
  sede_activa: boolean
  total: number
  disponibles: number
  prestados: number
  reservados: number
  en_transito: number
  en_revision: number
  consulta_en_sala: number
}

export type DisponibilidadLibro = {
  libro_id: number
  titulo: string
  isbn: string
  disponibles: number
  sedes: DisponibilidadSede[]
}

export type Prestamo = {
  id: number
  tipo: 'LOCAL' | 'INTERSEDES'
  estado: EstadoPrestamo
  socio: string
  numero_socio: number
  titulo: string
  codigo_inventario: string
  sede_origen: string
  sede_destino: string
  fecha_solicitud: string
  fecha_limite_retiro: string | null
  fecha_inicio: string | null
  fecha_vencimiento: string | null
  fecha_cierre: string | null
  motivo_cancelacion: string | null
  vencido: boolean
  dias_atraso: number
  retiro_vencido: boolean
}

export type Remito = {
  id: number
  numero: string
  sentido: 'IDA' | 'VUELTA'
  estado: EstadoRemito
  prestamo_id: number | null
  socio: string | null
  codigo_inventario: string
  titulo: string
  sede_origen: string
  sede_destino: string
  fecha_generacion: string
  fecha_despacho: string | null
  fecha_recepcion: string | null
  resultado_revision: ResultadoRevision | null
  observacion_revision: string | null
  dias_en_transito: number | null
  demorado: boolean
}

export type MovimientoRemito = {
  id: number
  estado_anterior: EstadoRemito | null
  estado_nuevo: EstadoRemito
  fecha_hora: string
  usuario: string
  observacion: string | null
}

export type Reserva = {
  id: number
  estado: EstadoReserva
  socio: string
  titulo: string
  sede: string
  fecha_solicitud: string
  fecha_asignacion: string | null
  fecha_limite: string | null
  fecha_cierre: string | null
  ejemplar_asignado: string | null
  posicion_cola: number | null
}

export type Devolucion = {
  id: number
  fecha_hora: string
  condicion_fisica: CondicionFisica
  observacion: string | null
  prestamo_id: number
  fecha_vencimiento: string | null
  socio: string
  titulo: string
  codigo_inventario: string
  sede: string
  registrado_por: string
  dias_atraso: number | null
  multa_monto: number | null
  multa_estado: EstadoMulta | null
}

export type Tablero = {
  prestamos_activos: number
  prestamos_vencidos: number
  prestamos_en_envio: number
  listos_para_retiro: number
  remitos_en_transito: number
  remitos_demorados: number
  reservas_pendientes: number
  reservas_asignadas: number
  multas_pendientes: number
  multas_pendientes_monto: number
  proximos_vencimientos: {
    id: number
    socio: string
    titulo: string
    sede: string
    fecha_vencimiento: string
    dias_restantes: number
  }[]
  ultimos_movimientos: {
    id: number
    remito_id: number
    numero: string
    titulo: string
    estado_nuevo: EstadoRemito
    fecha_hora: string
    usuario: string
  }[]
}

export type MovimientoSedes = {
  envios_totales: number
  dias_promedio_transito: number | null
  rutas: {
    sede_origen: string
    sede_destino: string
    envios: number
    recibidos: number
    en_curso: number
    extraviados: number
    dias_promedio_transito: number | null
  }[]
}

export type EnviosExitosos = {
  total: number
  exitosos: number
  tasa_exito: number | null
  incidencias: { danados: number; destruidos: number; extraviados: number }
  por_sede: {
    sede_id: number
    sede: string
    total: number
    exitosos: number
    incidencias: number
    tasa_exito: number | null
  }[]
}

export type LibroSolicitado = {
  libro_id: number
  titulo: string
  isbn: string
  solicitudes: number
  socios: number
  sedes_destino: number
}

export type VencidosMultas = {
  vencidos: {
    id: number
    socio: string
    titulo: string
    sede: string
    fecha_vencimiento: string
    dias_atraso: number
  }[]
  multas_por_socio: {
    socio_id: number
    socio: string
    cantidad: number
    pendiente: number
    saldado: number
  }[]
  total_pendiente: number
  total_saldado: number
}
