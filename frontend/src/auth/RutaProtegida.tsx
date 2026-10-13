import { Navigate, Outlet, useLocation } from 'react-router'
import { useSesion } from './contexto'
import styles from './auth.module.css'

/** Deja pasar solo con sesión iniciada; si no, manda al login.
 *
 * Si la sesión expiró, el login recuerda la pantalla para volver a ella. Si el usuario la cerró
 * a propósito, no: el próximo que ingrese empieza en el tablero. */
export function RutaProtegida() {
  const { estado, cierreVoluntario } = useSesion()
  const ubicacion = useLocation()

  if (estado === 'cargando') return <p className={styles.validando}>Validando la sesión…</p>
  if (estado === 'anonima') {
    const recordar = cierreVoluntario ? undefined : { desde: ubicacion }
    return <Navigate to="/login" replace state={recordar} />
  }
  return <Outlet />
}
