import { apiFetch } from './client'
import type { TokenSesion, UsuarioActual } from './tipos'

/** El login usa form-data (formato OAuth2 del backend), no JSON. */
export function pedirToken(username: string, password: string): Promise<TokenSesion> {
  return apiFetch<TokenSesion>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  })
}

export function pedirUsuarioActual(): Promise<UsuarioActual> {
  return apiFetch<UsuarioActual>('/auth/yo')
}
