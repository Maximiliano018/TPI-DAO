import type { ReactNode } from 'react'
import styles from './PageHeader.module.css'

type Props = {
  titulo: string
  descripcion?: string
  acciones?: ReactNode
}

/** Título de página con descripción y botones de acción a la derecha. */
export function PageHeader({ titulo, descripcion, acciones }: Props) {
  return (
    <header className={styles.header}>
      <div>
        <h1 className={styles.titulo}>{titulo}</h1>
        {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
      </div>
      {acciones && <div className={styles.acciones}>{acciones}</div>}
    </header>
  )
}
