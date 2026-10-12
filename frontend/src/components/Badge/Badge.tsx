import type { ReactNode } from 'react'
import styles from './Badge.module.css'

export type VarianteBadge = 'neutral' | 'primario' | 'info' | 'exito' | 'advertencia' | 'peligro'

type Props = {
  variante?: VarianteBadge
  children: ReactNode
}

/** Etiqueta chica con color según el significado. Siempre lleva texto, no solo color. */
export function Badge({ variante = 'neutral', children }: Props) {
  return <span className={`${styles.badge} ${styles[variante]}`}>{children}</span>
}
