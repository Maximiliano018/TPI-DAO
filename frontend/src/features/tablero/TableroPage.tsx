import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../api/client'
import styles from './TableroPage.module.css'

type Health = { estado: string; base_de_datos: string }

// Tablero principal. Por ahora muestra el estado de la conexión; acá irán las cifras de los reportes.
export function TableroPage() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/health'),
  })

  return (
    <main className={styles.pagina}>
      <h1 className={styles.titulo}>Sistema de Préstamos Interbibliotecarios</h1>

      <section className={styles.tarjeta}>
        <h2 className={styles.subtitulo}>Conexión con el backend</h2>
        {health.isPending && <p className={styles.info}>Consultando…</p>}
        {health.isError && (
          <p className={styles.error}>
            Sin conexión: {health.error.message}. ¿Está corriendo el backend en el puerto 8000?
          </p>
        )}
        {health.isSuccess && (
          <p className={styles.ok}>
            API: {health.data.estado} · Base de datos: {health.data.base_de_datos}
          </p>
        )}
      </section>
    </main>
  )
}
