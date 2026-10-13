import { useEliminarLibro } from '../../api/consultas'
import type { Libro } from '../../api/tipos'
import { Button } from '../../components/Button/Button'
import styles from '../comun/formulario.module.css'

type Props = {
  libro: Libro
  alTerminar: (eliminado: boolean) => void
}

/** Confirmación de borrado. Si el libro tiene historial, el back lo rechaza y se muestra el motivo. */
export function EliminarLibro({ libro, alTerminar }: Props) {
  const eliminar = useEliminarLibro()

  return (
    <div className={styles.formulario}>
      <p>
        ¿Eliminar <strong>{libro.titulo}</strong> del catálogo? Solo se puede si no tiene
        ejemplares ni reservas.
      </p>

      {eliminar.isError && <p className={styles.error}>{eliminar.error.message}</p>}

      <div className={styles.botones}>
        <Button variante="ghost" onClick={() => alTerminar(false)}>
          {eliminar.isError ? 'Cerrar' : 'Cancelar'}
        </Button>
        {!eliminar.isError && (
          <Button
            variante="peligro"
            disabled={eliminar.isPending}
            onClick={() => eliminar.mutate(libro.id, { onSuccess: () => alTerminar(true) })}
          >
            {eliminar.isPending ? 'Eliminando…' : 'Eliminar'}
          </Button>
        )}
      </div>
    </div>
  )
}
