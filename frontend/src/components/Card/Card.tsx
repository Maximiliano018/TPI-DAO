import type { ReactNode } from 'react'
import styles from './Card.module.css'

type Props = {
  titulo?: string
  descripcion?: string
  acciones?: ReactNode
  /** Sin relleno interno: para que una tabla ocupe todo el ancho. */
  sinRelleno?: boolean
  children: ReactNode
}

export function Card({ titulo, descripcion, acciones, sinRelleno = false, children }: Props) {
  return (
    <section className={styles.card}>
      {(titulo || acciones) && (
        <header className={styles.encabezado}>
          <div>
            {titulo && <h2 className={styles.titulo}>{titulo}</h2>}
            {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
          </div>
          {acciones}
        </header>
      )}
      <div className={sinRelleno ? styles.cuerpoSinRelleno : styles.cuerpo}>{children}</div>
    </section>
  )
}
