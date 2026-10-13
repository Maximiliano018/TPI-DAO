import { useState, type FormEvent } from 'react'
import { useDefinirHorarios } from '../../api/consultas'
import type { Franja, Sede } from '../../api/tipos'
import { Button } from '../../components/Button/Button'
import { claseControl } from '../../components/Field/control'
import comun from '../comun/formulario.module.css'
import { hora } from '../comun/formato'
import styles from './SedesPage.module.css'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

type Props = {
  sede: Sede
  alTerminar: () => void
}

/** Reemplaza todos los horarios de la sede. Un día puede tener varias franjas (horario cortado);
 * que no se superpongan lo valida el back. */
export function HorariosForm({ sede, alTerminar }: Props) {
  const definir = useDefinirHorarios()
  // El input de hora trabaja con "HH:MM"; el back devuelve "HH:MM:SS".
  const [franjas, setFranjas] = useState<Franja[]>(() =>
    sede.horarios.map((h) => ({
      dia_semana: h.dia_semana,
      hora_apertura: hora(h.hora_apertura),
      hora_cierre: hora(h.hora_cierre),
    })),
  )

  const cambiar = (indice: number, cambios: Partial<Franja>) =>
    setFranjas(franjas.map((f, i) => (i === indice ? { ...f, ...cambios } : f)))
  const quitar = (indice: number) => setFranjas(franjas.filter((_, i) => i !== indice))
  const agregar = () =>
    setFranjas([...franjas, { dia_semana: 1, hora_apertura: '08:00', hora_cierre: '20:00' }])

  function guardar(e: FormEvent) {
    e.preventDefault()
    definir.mutate({ id: sede.id, franjas }, { onSuccess: alTerminar })
  }

  return (
    <form className={comun.formulario} onSubmit={guardar}>
      {franjas.length === 0 && <p className={comun.aviso}>La sede no tiene horarios cargados.</p>}

      {franjas.map((f, i) => (
        <div key={i} className={styles.franja}>
          <select
            className={claseControl}
            aria-label="Día"
            value={f.dia_semana}
            onChange={(e) => cambiar(i, { dia_semana: Number(e.target.value) })}
          >
            {DIAS.map((dia, indice) => (
              <option key={dia} value={indice + 1}>
                {dia}
              </option>
            ))}
          </select>
          <input
            className={claseControl}
            type="time"
            aria-label="Apertura"
            required
            value={f.hora_apertura}
            onChange={(e) => cambiar(i, { hora_apertura: e.target.value })}
          />
          <input
            className={claseControl}
            type="time"
            aria-label="Cierre"
            required
            value={f.hora_cierre}
            onChange={(e) => cambiar(i, { hora_cierre: e.target.value })}
          />
          <Button tamano="chico" variante="ghost" onClick={() => quitar(i)}>
            Quitar
          </Button>
        </div>
      ))}

      <div>
        <Button tamano="chico" variante="secondary" onClick={agregar}>
          Agregar franja
        </Button>
      </div>

      {definir.isError && <p className={comun.error}>{definir.error.message}</p>}

      <div className={comun.botones}>
        <Button variante="ghost" onClick={alTerminar}>
          Cancelar
        </Button>
        <Button type="submit" disabled={definir.isPending}>
          {definir.isPending ? 'Guardando…' : 'Guardar horarios'}
        </Button>
      </div>
    </form>
  )
}
