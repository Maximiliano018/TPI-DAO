import type { ReactNode } from 'react'
import styles from './Grid.module.css'

type Props = {
  children: ReactNode
  /** Ancho mínimo de cada columna antes de pasar a la fila siguiente. */
  columna?: 'angosta' | 'ancha'
}

/** Grilla que acomoda sus hijos en tantas columnas como entren. */
export function Grid({ children, columna = 'angosta' }: Props) {
  return <div className={`${styles.grid} ${styles[columna]}`}>{children}</div>
}
