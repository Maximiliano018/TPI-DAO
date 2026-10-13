// Qué rol ve cada sección (ARCHITECTURE.md §6.1). Es la única definición: de acá salen el
// menú y la protección de las rutas. La autorización real la hace el backend; esto evita
// mostrar lo que el usuario no puede usar.
import type { Rol } from '../api/tipos'

export const TODOS: readonly Rol[] = ['ADMIN', 'BIBLIOTECARIO', 'LOGISTICA']
/** Atención al socio: circulación, socios y mantenimiento del catálogo. */
export const ATENCION: readonly Rol[] = ['ADMIN', 'BIBLIOTECARIO']
export const SOLO_ADMIN: readonly Rol[] = ['ADMIN']

export type ColorLibro = 'teal' | 'azul' | 'naranja' | 'mostaza'

export type Seccion = {
  ruta: string
  nombre: string
  /** Estante del menú donde se apoya (null = arriba de todo). */
  estante: 'Operación' | 'Administración' | 'Análisis' | null
  color: ColorLibro
  roles: readonly Rol[]
}

export const SECCIONES: readonly Seccion[] = [
  { ruta: '/', nombre: 'Tablero', estante: null, color: 'teal', roles: TODOS },
  { ruta: '/prestamos', nombre: 'Préstamos', estante: 'Operación', color: 'mostaza', roles: ATENCION },
  { ruta: '/envios', nombre: 'Envíos', estante: 'Operación', color: 'azul', roles: TODOS },
  { ruta: '/reservas', nombre: 'Reservas', estante: 'Operación', color: 'naranja', roles: ATENCION },
  { ruta: '/devoluciones', nombre: 'Devoluciones', estante: 'Operación', color: 'teal', roles: ATENCION },
  { ruta: '/disponibilidad', nombre: 'Disponibilidad', estante: 'Operación', color: 'azul', roles: TODOS },
  { ruta: '/sedes', nombre: 'Sedes', estante: 'Administración', color: 'naranja', roles: TODOS },
  { ruta: '/socios', nombre: 'Socios', estante: 'Administración', color: 'mostaza', roles: ATENCION },
  { ruta: '/catalogo', nombre: 'Catálogo', estante: 'Administración', color: 'teal', roles: TODOS },
  { ruta: '/reportes', nombre: 'Reportes', estante: 'Análisis', color: 'teal', roles: TODOS },
]

export function seccionDe(ruta: string): Seccion | undefined {
  return SECCIONES.find((s) => s.ruta === ruta)
}

export function puedeVer(rol: Rol, seccion: Seccion): boolean {
  return seccion.roles.includes(rol)
}
