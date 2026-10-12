import styles from './StatCard.module.css'

type Props = {
  etiqueta: string
  valor: string
}

/** Cifra destacada para el tablero. */
export function StatCard({ etiqueta, valor }: Props) {
  return (
    <div className={styles.card}>
      <span className={styles.etiqueta}>{etiqueta}</span>
      <span className={styles.valor}>{valor}</span>
    </div>
  )
}
