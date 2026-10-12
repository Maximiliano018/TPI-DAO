// Cliente HTTP de la API. En desarrollo, Vite redirige /api al backend (ver vite.config.ts).
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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
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
