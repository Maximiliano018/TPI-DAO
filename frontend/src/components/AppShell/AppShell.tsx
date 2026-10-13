import { NavLink, Outlet } from 'react-router'
import { useSedes } from '../../api/consultas'
import { NOMBRE_ROL, useSesion } from '../../auth/contexto'
import { puedeVer, SECCIONES } from '../../auth/permisos'
import styles from './AppShell.module.css'

const ESTANTES = [null, 'Operación', 'Administración', 'Análisis'] as const

/** Estructura común de todas las pantallas: biblioteca lateral + contenido. */
export function AppShell() {
  const { usuario } = useSesion()
  // Cada estante agrupa las secciones que el rol puede ver; cada sección es un libro de color.
  const estantes = ESTANTES.map((nombre) => ({
    nombre,
    libros: SECCIONES.filter((s) => s.estante === nombre && usuario && puedeVer(usuario.rol, s)),
  })).filter((e) => e.libros.length > 0)

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.marca}>
          <img src="/logo.png" alt="" width={44} height={44} />
          <span>Biblioteca</span>
        </div>

        <nav className={styles.nav} aria-label="Secciones">
          {estantes.map((estante) => (
            <div key={estante.nombre ?? 'inicio'} className={styles.estante}>
              {estante.nombre && <span className={styles.estanteNombre}>{estante.nombre}</span>}
              <div className={styles.libros}>
                {estante.libros.map((libro) => (
                  <NavLink
                    key={libro.ruta}
                    to={libro.ruta}
                    end
                    className={({ isActive }) =>
                      [styles.libro, styles[libro.color], isActive && styles.activo]
                        .filter(Boolean)
                        .join(' ')
                    }
                  >
                    {libro.nombre}
                  </NavLink>
                ))}
              </div>
              <div className={styles.repisa} />
            </div>
          ))}
        </nav>

        <UsuarioDeLaSesion />
      </aside>

      <main className={styles.contenido}>
        <Outlet />
      </main>
    </div>
  )
}

/** Quién está trabajando (nombre, rol y sede) y el botón para salir. */
function UsuarioDeLaSesion() {
  const { usuario, cerrarSesion } = useSesion()
  const sedes = useSedes()
  if (!usuario) return null

  const sede = sedes.data?.find((s) => s.id === usuario.sede_id)
  const detalle = [NOMBRE_ROL[usuario.rol], sede?.nombre ?? (usuario.sede_id ? null : 'Toda la red')]

  return (
    <div className={styles.usuario}>
      <span className={styles.usuarioNombre}>{usuario.nombre_completo}</span>
      <span className={styles.usuarioDetalle}>{detalle.filter(Boolean).join(' · ')}</span>
      <button type="button" className={styles.salir} onClick={cerrarSesion}>
        Cerrar sesión
      </button>
    </div>
  )
}
