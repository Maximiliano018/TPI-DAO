import type { ReactNode } from 'react'
import styles from './Field.module.css'

type Props = {
  etiqueta: string
  children: ReactNode
}

/** Etiqueta + control de formulario (input, select). */
export function Field({ etiqueta, children }: Props) {
  return (
    <label className={styles.campo}>
      <span className={styles.etiqueta}>{etiqueta}</span>
      {children}
    </label>
  )
}

