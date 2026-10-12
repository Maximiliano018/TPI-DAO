import { useMovimientosRemito } from '../../api/consultas'
import type { Remito } from '../../api/tipos'
import { Resultado } from '../../components/Resultado/Resultado'
import { EstadoBadge } from '../comun/EstadoBadge'
import { fechaHora } from '../comun/formato'
import styles from './RemitoTimeline.module.css'

/** Línea de tiempo con cada cambio de estado del remito (tabla movimiento_remito). */
export function RemitoTimeline({ remito }: { remito: Remito }) {
  const movimientos = useMovimientosRemito(remito.id)

  return (
    <Resultado consulta={movimientos}>
      {(lista) => (
        <ol className={styles.linea}>
          {lista.map((m) => (
            <li key={m.id} className={styles.paso}>
              <span className={styles.punto} aria-hidden="true" />
              <div className={styles.contenido}>
                <EstadoBadge entidad="remito" estado={m.estado_nuevo} />
                <span className={styles.cuando}>{fechaHora(m.fecha_hora)}</span>
                <span className={styles.detalle}>
                  {m.usuario}
                  {m.observacion && ` · ${m.observacion}`}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Resultado>
  )
}
