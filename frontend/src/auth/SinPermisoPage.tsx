import { useLocation, useNavigate } from 'react-router'
import { Button } from '../components/Button/Button'
import { Card } from '../components/Card/Card'
import { PageHeader } from '../components/PageHeader/PageHeader'
import { NOMBRE_ROL, useSesion } from './contexto'
import styles from './auth.module.css'

/** Página a la que se llega al abrir una sección que el rol no puede ver. */
export function SinPermisoPage() {
  const { usuario } = useSesion()
  const navegar = useNavigate()
  const seccion = (useLocation().state as { seccion?: string } | null)?.seccion

  return (
    <>
      <PageHeader titulo="Acceso restringido" />
      <Card>
        <div className={styles.sinPermiso}>
          <span className={styles.candado} aria-hidden="true">
            🔒
          </span>
          <p>
            {seccion ? (
              <>
                La sección <strong>{seccion}</strong> está bloqueada para tu rol
              </>
            ) : (
              <>Esta sección está bloqueada para tu rol</>
            )}
            {usuario && <> ({NOMBRE_ROL[usuario.rol]})</>}.
          </p>
          <p className={styles.ayuda}>
            Si necesitás acceder, pedile a un administrador de la red que revise tus permisos.
          </p>
          <Button onClick={() => navegar('/', { replace: true })}>Volver al panel</Button>
        </div>
      </Card>
    </>
  )
}
