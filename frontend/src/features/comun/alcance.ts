import { useSedes } from '../../api/consultas'
import { useSesion } from '../../auth/contexto'

/** Qué datos se están viendo: "toda la red" (ADMIN) o el nombre de la sede del usuario. */
export function useAlcance(): string {
  const { usuario } = useSesion()
  const sedes = useSedes()
  if (!usuario || usuario.rol === 'ADMIN') return 'toda la red'
  return sedes.data?.find((s) => s.id === usuario.sede_id)?.nombre ?? 'tu sede'
}
