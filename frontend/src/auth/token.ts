// Guarda el token de la sesión en el navegador. Sobrevive a recargar la página y dura lo
// que el backend indica en `expira_en` (una jornada).
//
// La fuente de verdad es `localStorage`: se lee en cada pedido, así que borrar la sesión
// desde el navegador (o desde otra pestaña) la cierra también en esta. Solo si el
// almacenamiento no está disponible (modo privado estricto) el token vive en memoria.

export const CLAVE_SESION = 'biblioteca.sesion'

type TokenGuardado = { token: string; expiraEn: string }

let respaldoEnMemoria: TokenGuardado | null = null

function leerGuardado(): TokenGuardado | null {
  try {
    const texto = localStorage.getItem(CLAVE_SESION)
    return texto ? (JSON.parse(texto) as TokenGuardado) : null
  } catch {
    return respaldoEnMemoria
  }
}

export function guardarToken(token: string, expiraEn: string): void {
  const guardado = { token, expiraEn }
  try {
    localStorage.setItem(CLAVE_SESION, JSON.stringify(guardado))
    respaldoEnMemoria = null
  } catch {
    respaldoEnMemoria = guardado
  }
}

/** Token vigente, o null si no hay sesión o ya expiró. */
export function leerToken(): string | null {
  const guardado = leerGuardado()
  if (!guardado?.token || new Date(guardado.expiraEn) <= new Date()) {
    if (guardado) borrarToken()
    return null
  }
  return guardado.token
}

export function borrarToken(): void {
  respaldoEnMemoria = null
  try {
    localStorage.removeItem(CLAVE_SESION)
  } catch {
    // Nada que borrar.
  }
}
