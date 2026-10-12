import { NavLink, Outlet } from 'react-router'
import styles from './AppShell.module.css'

// Cada estante agrupa secciones; cada sección se dibuja como un libro de color apoyado en el estante.
const ESTANTES = [
  { nombre: null, libros: [{ ruta: '/', nombre: 'Tablero', color: 'teal' }] },
  {
    nombre: 'Operación',
    libros: [
      { ruta: '/prestamos', nombre: 'Préstamos', color: 'mostaza' },
      { ruta: '/envios', nombre: 'Envíos', color: 'azul' },
      { ruta: '/reservas', nombre: 'Reservas', color: 'naranja' },
      { ruta: '/devoluciones', nombre: 'Devoluciones', color: 'teal' },
      { ruta: '/disponibilidad', nombre: 'Disponibilidad', color: 'azul' },
    ],
  },
  {
    nombre: 'Administración',
    libros: [
      { ruta: '/sedes', nombre: 'Sedes', color: 'naranja' },
      { ruta: '/socios', nombre: 'Socios', color: 'mostaza' },
      { ruta: '/catalogo', nombre: 'Catálogo', color: 'teal' },
    ],
  },
  { nombre: 'Análisis', libros: [{ ruta: '/reportes', nombre: 'Reportes', color: 'teal' }] },
]

/** Estructura común de todas las pantallas: biblioteca lateral + contenido. */
export function AppShell() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.marca}>
          <img src="/logo.png" alt="" width={44} height={44} />
          <span>Biblioteca</span>
        </div>

        <nav className={styles.nav} aria-label="Secciones">
          {ESTANTES.map((estante) => (
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
      </aside>

      <main className={styles.contenido}>
        <Outlet />
      </main>
    </div>
  )
}
