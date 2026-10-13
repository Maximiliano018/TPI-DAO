import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate, type Location } from 'react-router'
import { Button } from '../components/Button/Button'
import { claseControl } from '../components/Field/control'
import { Field } from '../components/Field/Field'
import { useSesion } from './contexto'
import styles from './auth.module.css'

export function LoginPage() {
  const { estado, iniciarSesion } = useSesion()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  // Vuelve a la pantalla que se quería abrir antes de pedir el login.
  const destino = (ubicacion.state as { desde?: Location } | null)?.desde?.pathname ?? '/'

  if (estado === 'iniciada') return <Navigate to={destino} replace />

  async function ingresar(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await iniciarSesion(usuario, contrasena)
      navegar(destino, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión')
      setContrasena('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className={styles.pantalla}>
      <form className={styles.tarjeta} onSubmit={ingresar} aria-labelledby="titulo-login">
        <div className={styles.marca}>
          <img src="/logo.png" alt="" width={56} height={56} />
          <div>
            <h1 id="titulo-login" className={styles.titulo}>
              Biblioteca
            </h1>
            <p className={styles.subtitulo}>Red de préstamos interbibliotecarios</p>
          </div>
        </div>

        <Field etiqueta="Usuario">
          <input
            className={claseControl}
            autoComplete="username"
            autoFocus
            required
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
          />
        </Field>
        <Field etiqueta="Contraseña">
          <input
            className={claseControl}
            type="password"
            autoComplete="current-password"
            required
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
          />
        </Field>

        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}

        <Button type="submit" disabled={enviando}>
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </Button>
      </form>
    </main>
  )
}
