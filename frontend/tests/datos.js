// Datos de ejemplo con la forma de las respuestas de la API.

export const ADMIN = {
  id: 1,
  nombre: 'Ana Admin',
  rol: 'ADMIN',
  sede_id: null,
  sede: null,
  permisos: [
    'CATALOGO_ADMINISTRAR',
    'CATALOGO_LEER',
    'EJEMPLAR_ADMINISTRAR',
    'EJEMPLAR_LEER',
    'PARAMETROS_ADMINISTRAR',
    'PRESTAMO_LEER',
    'REMITO_EXTRAVIO',
    'REMITO_LEER',
    'MULTA_LEER',
    'MULTA_SALDAR',
    'RESERVA_LEER',
    'SEDE_ADMINISTRAR',
    'SEDE_LEER_BASICO',
    'SEDE_LEER_COMPLETO',
    'SEDE_LEER_PUBLICO',
    'SEDE_VER_HISTORIAL',
    'SOCIO_ADMINISTRAR',
    'SOCIO_LEER',
    'SOCIO_REGISTRAR',
    'TAREAS_EJECUTAR',
    'USUARIO_ADMINISTRAR',
  ],
};

export const BIBLIOTECARIO = {
  id: 2,
  nombre: 'Lucía Gómez',
  rol: 'BIBLIOTECARIO',
  sede_id: 1,
  sede: { id: 1, codigo: 'CEN', nombre: 'Sede Central' },
  permisos: [
    'CATALOGO_LEER',
    'DEVOLUCION_REGISTRAR',
    'EJEMPLAR_ADMINISTRAR',
    'EJEMPLAR_LEER',
    'MULTA_LEER',
    'MULTA_SALDAR',
    'PRESTAMO_LEER',
    'PRESTAMO_REGISTRAR',
    'REMITO_EXTRAVIO',
    'REMITO_LEER',
    'REMITO_OPERAR',
    'RESERVA_LEER',
    'RESERVA_REGISTRAR',
    'SEDE_LEER_BASICO',
    'SEDE_LEER_PUBLICO',
    'SOCIO_LEER',
    'SOCIO_REGISTRAR',
  ],
};

export const SOCIO = {
  id: 3,
  nombre: 'Sol Socia',
  rol: 'SOCIO',
  sede_id: null,
  sede: null,
  socio_id: 45,
  permisos: [
    'CATALOGO_LEER',
    'MULTA_VER_PROPIAS',
    'PRESTAMO_VER_PROPIOS',
    'RESERVA_PROPIA',
    'SEDE_LEER_PUBLICO',
    'SOCIO_VER_PROPIO',
  ],
};

const SEMANA = [1, 2, 3, 4, 5, 6, 7].map((dia) => ({
  dia_semana: dia,
  apertura: '00:00',
  cierre: '23:59',
}));

/** Sede con el esquema de administrador; `over` pisa cualquier campo. */
export function sedeAdmin(over = {}) {
  return {
    id: 1,
    codigo: 'CEN',
    nombre: 'Sede Central',
    estado: 'ACTIVA',
    direccion: {
      calle: 'Av. Colón',
      numero: '1250',
      localidad_id: 1,
      localidad: 'Córdoba',
      provincia: 'Córdoba',
    },
    contacto: {
      telefono: '+543514221234',
      email: 'central@red.example',
      responsable: 'Laura Pérez',
    },
    horarios: SEMANA,
    excepciones: [],
    abierta_ahora: true,
    baja: null,
    version: 1,
    creado_en: '2026-10-14T15:30:00Z',
    creado_por: { id: 1, nombre: 'Ana Admin' },
    actualizado_en: '2026-10-14T15:30:00Z',
    actualizado_por: { id: 1, nombre: 'Ana Admin' },
    ...over,
  };
}

function omitir(objeto, claves) {
  return Object.fromEntries(Object.entries(objeto).filter(([clave]) => !claves.includes(clave)));
}

/** Esquema de bibliotecario: sin baja, versión ni auditoría. */
export function sedeBasica(over = {}) {
  return omitir(sedeAdmin(over), [
    'baja',
    'version',
    'creado_en',
    'creado_por',
    'actualizado_en',
    'actualizado_por',
  ]);
}

/** Esquema de socio: sin estado ni responsable. */
export function sedePublica(over = {}) {
  const basica = omitir(sedeBasica(over), ['estado']);
  return {
    ...basica,
    contacto: { telefono: basica.contacto.telefono, email: basica.contacto.email },
  };
}

export function pagina(items, over = {}) {
  return { items, total: items.length, page: 1, size: 20, ...over };
}

export const LOCALIDADES = [
  { id: 1, nombre: 'Córdoba', departamento: 'Capital', provincia_id: 1, provincia: 'Córdoba' },
  {
    id: 2,
    nombre: 'Villa María',
    departamento: 'General San Martín',
    provincia_id: 1,
    provincia: 'Córdoba',
  },
  {
    id: 3,
    nombre: 'Río Cuarto',
    departamento: 'Río Cuarto',
    provincia_id: 1,
    provincia: 'Córdoba',
  },
];

export function excepcion(over = {}) {
  return {
    id: 7,
    fecha: '2026-12-24',
    tipo: 'CIERRE_TOTAL',
    hora_desde: null,
    hora_hasta: null,
    motivo: 'Víspera de Navidad',
    ...over,
  };
}

export function evento(over = {}) {
  return {
    id: 1,
    tipo_evento: 'MODIFICACION',
    fecha_hora: '2026-10-15T12:00:00Z',
    usuario: { id: 1, nombre: 'Ana Admin' },
    estado_anterior: null,
    estado_nuevo: null,
    motivo: null,
    version_resultante: 2,
    cambios: [{ campo: 'telefono', antes: '+543514221234', despues: '+543514229999' }],
    ...over,
  };
}

/** Usuario del personal con la forma de `GET /usuarios`. */
export function usuarioPersonal(over = {}) {
  return {
    id: 10,
    username: 'lucia.gomez',
    nombre: 'Lucía Gómez',
    rol: 'BIBLIOTECARIO',
    activo: true,
    sede_id: 1,
    sede: { id: 1, codigo: 'CEN', nombre: 'Sede Central' },
    creado_en: '2026-10-14T15:30:00Z',
    creado_por: { id: 1, nombre: 'Ana Admin' },
    actualizado_en: '2026-10-14T15:30:00Z',
    actualizado_por: { id: 1, nombre: 'Ana Admin' },
    ...over,
  };
}

/** Socio con el formato de `GET /socios/{id}` (ficha con situación); `over` pisa cualquier campo. */
export function socio(over = {}) {
  return {
    id: 45,
    numero_socio: '00045',
    tipo_documento: 'DNI',
    nro_documento: '30111222',
    nombre: 'Sol',
    apellido: 'Socia',
    estado: 'HABILITADO',
    motivo_inhabilitacion: null,
    sede_alta_id: 1,
    sede_alta: 'Sede Central',
    fecha_nacimiento: '1995-04-12',
    email: 'sol@example.com',
    telefono: '+543515000000',
    domicilio: 'San Martín 123',
    causas_inhabilitacion: [],
    motivo_administrativo: null,
    fecha_alta: '2026-10-14T15:30:00Z',
    fecha_baja: null,
    motivo_baja: null,
    creado_por: { id: 2, nombre: 'Lucía Gómez' },
    actualizado_en: '2026-10-14T15:30:00Z',
    actualizado_por: { id: 2, nombre: 'Lucía Gómez' },
    cuenta: null,
    situacion: {
      prestamos_activos: 0,
      prestamos_vencidos: 0,
      multas_pendientes: 0,
      reservas_activas: 0,
    },
    ...over,
  };
}

/** Libro con el formato de la API; `over` pisa cualquier campo. */
export function libro(over = {}) {
  return {
    id: 12,
    isbn: '9789500705783',
    titulo: 'Rayuela',
    autores: ['Julio Cortázar'],
    editorial: 'Sudamericana',
    anio_edicion: 1963,
    categoria: { id: 1, nombre: 'Literatura argentina' },
    tipo_material: 'LIBRO',
    ejemplares: 3,
    disponibles: 1,
    creado_en: '2026-10-14T15:30:00Z',
    creado_por: { id: 1, nombre: 'Ana Admin' },
    actualizado_en: '2026-10-14T15:30:00Z',
    actualizado_por: { id: 1, nombre: 'Ana Admin' },
    ...over,
  };
}

export const CATEGORIAS = [
  { id: 1, nombre: 'Literatura argentina' },
  { id: 2, nombre: 'Historia' },
];

/** Ejemplar con el formato de `GET /ejemplares/{id}` (con historial). */
export function ejemplar(over = {}) {
  return {
    id: 301,
    codigo_inventario: 'CEN-000123',
    libro_id: 12,
    libro: 'Rayuela',
    sede_propietaria_id: 1,
    sede_propietaria: 'Sede Central',
    sede_actual_id: 1,
    sede_actual: 'Sede Central',
    estado_fisico: 'BUENO',
    estado: 'DISPONIBLE',
    observaciones: null,
    fecha_baja: null,
    motivo_baja: null,
    version: 1,
    historial: [
      {
        estado_anterior: null,
        estado_nuevo: 'DISPONIBLE',
        fecha_hora: '2026-10-14T15:30:00Z',
        usuario: { id: 2, nombre: 'Lucía Gómez' },
        observacion: 'Alta',
      },
    ],
    ...over,
  };
}

/** Préstamo con el formato de `GET /prestamos/{id}` (con historial y remitos). */
export function prestamo(over = {}) {
  return {
    id: 118,
    numero: 'P-2026-000118',
    tipo: 'LOCAL',
    estado: 'SOLICITADO',
    socio_id: 45,
    socio: 'Sol Socia',
    numero_socio: '00045',
    ejemplar_id: 301,
    codigo_ejemplar: 'CEN-000123',
    libro_id: 12,
    libro: 'Rayuela',
    sede_origen_id: 1,
    sede_origen: 'Sede Central',
    sede_destino_id: 1,
    sede_destino: 'Sede Central',
    fecha_solicitud: '2026-11-10T15:00:00Z',
    fecha_inicio: null,
    fecha_vencimiento: null,
    fecha_devolucion: null,
    renovaciones: 0,
    registrado_por: { id: 2, nombre: 'Lucía Gómez' },
    historial: [
      {
        estado_anterior: null,
        estado_nuevo: 'SOLICITADO',
        fecha_hora: '2026-11-10T15:00:00Z',
        usuario: { id: 2, nombre: 'Lucía Gómez' },
        observacion: 'Solicitud registrada',
      },
    ],
    remitos: [],
    devolucion: null,
    multa: null,
    ...over,
  };
}

/** Remito con el formato de `GET /remitos/{id}` (con movimientos e incidencias). */
export function remito(over = {}) {
  return {
    id: 51,
    numero: 'R-2026-000051',
    motivo: 'ENVIO',
    estado: 'GENERADO',
    sede_origen_id: 1,
    sede_origen: 'Sede Central',
    sede_destino_id: 2,
    sede_destino: 'Sede Norte',
    fecha_generacion: '2026-11-10T15:00:00Z',
    fecha_despacho: null,
    fecha_recepcion: null,
    observaciones: null,
    lineas: [
      {
        ejemplar_id: 301,
        codigo_ejemplar: 'CEN-000123',
        libro: 'Rayuela',
        prestamo_id: 118,
        estado_fisico_salida: 'BUENO',
        estado_fisico_llegada: null,
        resultado: null,
        observacion: null,
      },
    ],
    movimientos: [
      {
        estado_anterior: null,
        estado_nuevo: 'GENERADO',
        fecha_hora: '2026-11-10T15:00:00Z',
        usuario: { id: 2, nombre: 'Lucía Gómez' },
        observacion: 'Remito generado',
      },
    ],
    incidencias: [],
    ...over,
  };
}

/** Reserva con el formato de la API; `over` pisa cualquier campo. */
export function reserva(over = {}) {
  return {
    id: 9,
    numero: 'RS-2026-000009',
    estado: 'PENDIENTE',
    socio_id: 45,
    socio: 'Sol Socia',
    numero_socio: '00045',
    libro_id: 12,
    libro: 'Rayuela',
    sede_retiro_id: 1,
    sede_retiro: 'Sede Central',
    fecha_reserva: '2026-11-10T15:00:00Z',
    posicion_en_cola: 2,
    ejemplar_id: null,
    codigo_ejemplar: null,
    vencimiento_retiro: null,
    prestamo_id: null,
    ...over,
  };
}

/** Multa con el formato de la API; `over` pisa cualquier campo. */
export function multa(over = {}) {
  return {
    id: 14,
    prestamo_id: 118,
    numero_prestamo: 'P-2026-000118',
    socio_id: 45,
    socio: 'Sol Socia',
    libro: 'Rayuela',
    dias_atraso: 5,
    monto_por_dia: '200.00',
    monto_total: '1000.00',
    estado: 'PENDIENTE',
    fecha_generacion: '2026-11-15T15:00:00Z',
    fecha_saldada: null,
    saldada_por: null,
    ...over,
  };
}
