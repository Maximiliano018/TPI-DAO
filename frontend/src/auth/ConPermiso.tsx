import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useSesion } from './contexto'
import { puedeVer, type Seccion } from './permisos'

type Props = {
  seccion: Seccion
  children: ReactNode
}

/** Muestra la sección si el rol la puede ver; si no, lleva a la página de acceso restringido
 * indicando qué sección se intentó abrir. */
export function ConPermiso({ seccion, children }: Props) {
  const { usuario } = useSesion()
  if (usuario && puedeVer(usuario.rol, seccion)) return <>{children}</>
  return <Navigate to="/sin-permiso" replace state={{ seccion: seccion.nombre }} />
}
