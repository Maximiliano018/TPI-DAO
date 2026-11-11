import { MENSAJES } from '../utils/mensajes.js';

/** Error de la API con el formato `{ codigo, mensaje, detalles }` y el estado HTTP. */
export class ApiError extends Error {
  constructor({ estado, codigo, mensaje, detalles = [] }) {
    super(mensaje);
    this.name = 'ApiError';
    this.estado = estado;
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.detalles = detalles;
  }
}

const CLAVE_TOKEN = 'tpi.token';
let token = null;
let alSesionVencida = () => {};

function almacen() {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

/** Token en memoria y en `sessionStorage` (sobrevive a una recarga, no al cierre de la pestaña). */
export function guardarToken(nuevo) {
  token = nuevo;
  try {
    if (nuevo) almacen()?.setItem(CLAVE_TOKEN, nuevo);
    else almacen()?.removeItem(CLAVE_TOKEN);
  } catch {
    /* sin almacenamiento disponible: queda solo en memoria */
  }
}

export function leerToken() {
  if (token) return token;
  try {
    token = almacen()?.getItem(CLAVE_TOKEN) ?? null;
  } catch {
    token = null;
  }
  return token;
}

/** Registra qué hacer cuando cualquier solicitud autenticada responde 401. */
export function alVencerLaSesion(callback) {
  alSesionVencida = callback;
}

function consulta(params) {
  const q = new URLSearchParams();
  for (const [clave, valor] of Object.entries(params ?? {})) {
    if (valor !== undefined && valor !== null && valor !== '') q.set(clave, String(valor));
  }
  const texto = q.toString();
  return texto ? `?${texto}` : '';
}

/**
 * Solicitud a la API. Agrega el token, convierte los errores a `ApiError` y, ante un 401 de una
 * solicitud autenticada, cierra la sesión.
 *
 * @param {string} ruta Ruta bajo `/api/v1` (por ejemplo `/sedes`).
 * @param {{method?: string, body?: unknown, params?: object, autenticada?: boolean}} [opciones]
 */
export async function solicitar(ruta, { method = 'GET', body, params, autenticada = true } = {}) {
  const encabezados = { Accept: 'application/json' };
  if (body !== undefined) encabezados['Content-Type'] = 'application/json';
  const actual = autenticada ? leerToken() : null;
  if (actual) encabezados.Authorization = `Bearer ${actual}`;

  let respuesta;
  try {
    respuesta = await fetch(`/api/v1${ruta}${consulta(params)}`, {
      method,
      headers: encabezados,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError({ estado: 0, codigo: 'SIN_CONEXION', mensaje: MENSAJES.sinConexion });
  }

  if (respuesta.status === 204) return null;
  const cuerpo = await respuesta.json().catch(() => null);
  if (respuesta.ok) return cuerpo;

  const error = new ApiError({
    estado: respuesta.status,
    codigo: cuerpo?.error?.codigo ?? `HTTP_${respuesta.status}`,
    mensaje: cuerpo?.error?.mensaje ?? MENSAJES.errorGeneral,
    detalles: cuerpo?.error?.detalles ?? [],
  });
  if (respuesta.status === 401 && autenticada && actual) alSesionVencida(error);
  throw error;
}

export const api = {
  get: (ruta, params) => solicitar(ruta, { params }),
  post: (ruta, body) => solicitar(ruta, { method: 'POST', body: body ?? {} }),
  put: (ruta, body) => solicitar(ruta, { method: 'PUT', body }),
  delete: (ruta) => solicitar(ruta, { method: 'DELETE' }),
};
