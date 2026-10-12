import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import styles from './Resultado.module.css'

type Props<T> = {
  consulta: UseQueryResult<T>
  children: (datos: T) => ReactNode
}

/** Muestra "cargando" o el error de una consulta; si salió bien, dibuja los datos. */
export function Resultado<T>({ consulta, children }: Props<T>) {
  if (consulta.isPending) return <p className={styles.mensaje}>Cargando…</p>
  if (consulta.isError)
    return (
      <p className={`${styles.mensaje} ${styles.error}`}>
        No se pudo cargar: {consulta.error.message}
      </p>
    )
  return <>{children(consulta.data)}</>
}
