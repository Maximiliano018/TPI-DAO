// Datos de ejemplo con la forma de las respuestas de la API.

export const ADMIN = {
  id: 1,
  nombre: 'Ana Admin',
  rol: 'ADMIN',
  sede_id: null,
  sede: null,
  permisos: [
    'SEDE_ADMINISTRAR',
    'SEDE_LEER_BASICO',
    'SEDE_LEER_COMPLETO',
    'SEDE_LEER_PUBLICO',
    'SEDE_VER_HISTORIAL',
    'USUARIO_ADMINISTRAR',
  ],
};

export const BIBLIOTECARIO = {
  id: 2,
  nombre: 'Lucía Gómez',
  rol: 'BIBLIOTECARIO',
  sede_id: 1,
  sede: { id: 1, codigo: 'CEN', nombre: 'Sede Central' },
  permisos: ['SEDE_LEER_BASICO', 'SEDE_LEER_PUBLICO'],
};

export const SOCIO = {
  id: 3,
  nombre: 'Sol Socia',
  rol: 'SOCIO',
  sede_id: null,
  sede: null,
  permisos: ['SEDE_LEER_PUBLICO'],
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
