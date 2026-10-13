import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { pedirToken, pedirUsuarioActual } from '../api/auth'
import { registrarAlPerderSesion } from '../api/client'
import type { UsuarioActual } from '../api/tipos'
import { ContextoSesion, type Sesion } from './contexto'
import { borrarToken, CLAVE_SESION, guardarToken, leerToken } from './token'

/** Mantiene quién inició sesión. Al abrir la app valida el token guardado contra /auth/yo. */
export function ProveedorSesion({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [estado, setEstado] = useState<Sesion['estado']>(() =>
    leerToken() ? 'cargando' : 'anonima',
  )
  const [usuario, setUsuario] = useState<UsuarioActual | null>(null)
  const [cierreVoluntario, setCierreVoluntario] = useState(false)

  const terminar = useCallback(
    (voluntario: boolean) => {
      borrarToken()
      // Los datos en caché son del usuario anterior: no deben verse en la próxima sesión.
      queryClient.clear()
      setUsuario(null)
      setCierreVoluntario(voluntario)
      setEstado('anonima')
    },
    [queryClient],
  )
  const cerrarSesion = useCallback(() => terminar(true), [terminar])

  useEffect(() => {
    // Token vencido o revocado: se vuelve al login recordando la pantalla.
    registrarAlPerderSesion(() => terminar(false))
  }, [terminar])

  useEffect(() => {
    // La sesión se cerró o se borró en otra pestaña: esta también vuelve al login.
    function alCambiarAlmacenamiento(evento: StorageEvent) {
      const esLaSesion = evento.key === CLAVE_SESION || evento.key === null
      if (esLaSesion && estado === 'iniciada' && !leerToken()) terminar(false)
    }
    window.addEventListener('storage', alCambiarAlmacenamiento)
    return () => window.removeEventListener('storage', alCambiarAlmacenamiento)
  }, [estado, terminar])

  useEffect(() => {
    if (estado !== 'cargando') return
    pedirUsuarioActual()
      .then((u) => {
        setUsuario(u)
        setEstado('iniciada')
      })
      .catch(() => terminar(false))
  }, [estado, terminar])

  const iniciarSesion = useCallback(async (username: string, password: string) => {
    const { access_token, expira_en } = await pedirToken(username, password)
    guardarToken(access_token, expira_en)
    try {
      setUsuario(await pedirUsuarioActual())
      setCierreVoluntario(false)
      setEstado('iniciada')
    } catch (error) {
      borrarToken()
      throw error
    }
  }, [])

  const sesion = useMemo<Sesion>(
    () => ({ estado, usuario, cierreVoluntario, iniciarSesion, cerrarSesion }),
    [estado, usuario, cierreVoluntario, iniciarSesion, cerrarSesion],
  )

  return <ContextoSesion.Provider value={sesion}>{children}</ContextoSesion.Provider>
}
