// Cliente HTTP de la API. En desarrollo, Vite redirige /api al backend (ver vite.config.ts).
import { borrarToken, leerToken } from '../auth/token'

const BASE_URL = '/api/v1'

/** Error de negocio devuelto por el backend con el formato {codigo, mensaje}. */
export class ApiError extends Error {
  readonly status: number
  readonly codigo: string

  constructor(status: number, codigo: string, mensaje: string) {
    super(mensaje)
    this.status = status
    this.codigo = codigo
  }
}

let alPerderSesion: () => void = () => {}

/** La sesión registra qué hacer si el backend responde 401 (token vencido o revocado). */
export function registrarAlPerderSesion(accion: () => void): void {
  alPerderSesion = accion
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = leerToken()
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
    // Un 401 significa que no hay sesión válida (expiró, la revocaron o se borró el token):
    // se vuelve al login. El 401 del propio login es "credenciales incorrectas", no eso.
    if (respuesta.status === 401 && path !== '/auth/login') {
      borrarToken()
      alPerderSesion()
    }
    throw new ApiError(
      respuesta.status,
      cuerpo?.codigo ?? 'ERROR_HTTP',
      cuerpo?.mensaje ?? `Error ${respuesta.status}`,
    )
  }

  // 204 (por ejemplo, al eliminar): no hay cuerpo.
  if (respuesta.status === 204) return undefined as T
  return (await respuesta.json()) as T
}
