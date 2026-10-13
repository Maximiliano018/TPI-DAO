import { useCambiarEstadoSede } from '../../api/consultas'
import type { Sede } from '../../api/tipos'
import { Button } from '../../components/Button/Button'
import styles from '../comun/formulario.module.css'

type Props = {
  sede: Sede
  alTerminar: () => void
}

/** Confirmación de baja o reactivación. Si la sede tiene préstamos, envíos o reservas en
 * curso, el back rechaza la baja y se muestra el motivo. */
export function CambiarEstadoSede({ sede, alTerminar }: Props) {
  const cambiar = useCambiarEstadoSede()
  const baja = sede.activa

  return (
    <div className={styles.formulario}>
      {baja ? (
        <p>
          ¿Dar de baja <strong>{sede.nombre}</strong>? No se podrán registrar préstamos, reservas
          ni envíos nuevos desde o hacia esta sede. Solo es posible si no tiene operaciones en
          curso.
        </p>
      ) : (
        <p>
          ¿Reactivar <strong>{sede.nombre}</strong>? Vuelve a operar normalmente.
        </p>
      )}

      {cambiar.isError && <p className={styles.error}>{cambiar.error.message}</p>}

      <div className={styles.botones}>
        <Button variante="ghost" onClick={alTerminar}>
          {cambiar.isError ? 'Cerrar' : 'Cancelar'}
        </Button>
        {!cambiar.isError && (
          <Button
            variante={baja ? 'peligro' : 'primary'}
            disabled={cambiar.isPending}
            onClick={() => cambiar.mutate(sede, { onSuccess: alTerminar })}
          >
            {cambiar.isPending ? 'Guardando…' : baja ? 'Dar de baja' : 'Reactivar'}
          </Button>
        )}
      </div>
    </div>
  )
}
