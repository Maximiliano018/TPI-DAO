import { api } from './client.js';

const ruta = (nombre) => (params) => api.get(`/reportes/${nombre}`, params);

export const movimientoEntreSedes = ruta('movimiento-entre-sedes');
export const enviosEIncidencias = ruta('envios-e-incidencias');
export const librosMasSolicitados = ruta('libros-mas-solicitados');
export const vencidosYMultas = ruta('vencidos-y-multas');
export const disponibilidadPorSede = ruta('disponibilidad-por-sede');
export const activosYEnTransito = ruta('prestamos-activos-y-en-transito');
