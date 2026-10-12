import type { ReactNode } from 'react'
import styles from './Table.module.css'

export type Columna<T> = {
  titulo: string
  celda: (fila: T) => ReactNode
  alinear?: 'izquierda' | 'derecha'
}

type Props<T> = {
  columnas: Columna<T>[]
  filas: T[]
  clave: (fila: T) => string | number
  vacio?: string
  /** Si se pasa, las filas se pueden seleccionar con un clic. */
  alSeleccionar?: (fila: T) => void
  seleccionada?: string | number | null
}

export function Table<T>({
  columnas,
  filas,
  clave,
  vacio = 'No hay datos para mostrar.',
  alSeleccionar,
  seleccionada,
}: Props<T>) {
  if (filas.length === 0) return <p className={styles.vacio}>{vacio}</p>

  return (
    <div className={styles.contenedor}>
      <table className={styles.tabla}>
        <thead>
          <tr>
            {columnas.map((c) => (
              <th key={c.titulo} className={c.alinear === 'derecha' ? styles.derecha : undefined}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => {
            const id = clave(fila)
            const clases = [
              alSeleccionar && styles.seleccionable,
              id === seleccionada && styles.seleccionada,
            ]
            return (
              <tr
                key={id}
                className={clases.filter(Boolean).join(' ') || undefined}
                onClick={alSeleccionar ? () => alSeleccionar(fila) : undefined}
              >
                {columnas.map((c) => (
                  <td key={c.titulo} className={c.alinear === 'derecha' ? styles.derecha : undefined}>
                    {c.celda(fila)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
