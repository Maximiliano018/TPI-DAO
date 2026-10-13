import { createContext, useContext } from 'react'
import type { Rol, UsuarioActual } from '../api/tipos'

export type Sesion = {
  /** `cargando` mientras se valida un token guardado al abrir la app. */
  estado: 'cargando' | 'anonima' | 'iniciada'
  usuario: UsuarioActual | null
  /** Verdadero si el usuario cerró la sesión a propósito (y no porque expiró). */
  cierreVoluntario: boolean
  iniciarSesion: (username: string, password: string) => Promise<void>
  cerrarSesion: () => void
}

export const ContextoSesion = createContext<Sesion | null>(null)

export function useSesion(): Sesion {
  const sesion = useContext(ContextoSesion)
  if (!sesion) throw new Error('useSesion debe usarse dentro de <ProveedorSesion>')
  return sesion
}

/** Verdadero si el usuario tiene alguno de los roles. La autorización real es del backend:
 * esto solo oculta lo que el usuario no puede hacer. */
export function useTieneRol(...roles: readonly Rol[]): boolean {
  const { usuario } = useSesion()
  return usuario !== null && roles.includes(usuario.rol)
}

/** Devuelve una función que dice si el usuario opera sobre un recurso de esas sedes:
 * el ADMIN en toda la red; el resto, solo si su sede está entre ellas (ARCHITECTURE.md §6.1). */
export function useOperaEnSede(): (...sedes: number[]) => boolean {
  const { usuario } = useSesion()
  return (...sedes) =>
    usuario !== null &&
    (usuario.rol === 'ADMIN' || (usuario.sede_id !== null && sedes.includes(usuario.sede_id)))
}

export const NOMBRE_ROL: Record<Rol, string> = {
  ADMIN: 'Administración',
  BIBLIOTECARIO: 'Bibliotecario/a',
  LOGISTICA: 'Logística',
}
