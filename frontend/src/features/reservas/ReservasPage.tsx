import { useState } from 'react'
import { useReservas } from '../../api/consultas'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { EstadoBadge } from '../comun/EstadoBadge'
import { fecha, fechaHora } from '../comun/formato'

export function ReservasPage() {
  const [soloAbiertas, setSoloAbiertas] = useState(true)
  const reservas = useReservas(soloAbiertas)

  return (
    <>
      <PageHeader
        titulo="Reservas"
        descripcion="Cola de espera (por orden de llegada) para libros sin ejemplares disponibles en la sede."
        acciones={<Button>Nueva reserva</Button>}
      />

      <div className={comun.filtros}>
        <Field etiqueta="Mostrar">
          <select
            className={claseControl}
            value={soloAbiertas ? 'abiertas' : 'todas'}
            onChange={(e) => setSoloAbiertas(e.target.value === 'abiertas')}
          >
            <option value="abiertas">En espera y asignadas</option>
            <option value="todas">Todas</option>
          </select>
        </Field>
      </div>

      <Card sinRelleno>
        <Resultado consulta={reservas}>
          {(lista) => (
            <Table
              filas={lista}
              clave={(r) => r.id}
              columnas={[
                {
                  titulo: 'Libro',
                  celda: (r) => (
                    <>
                      {r.titulo}
                      <span className={comun.sub}>Retira en {r.sede}</span>
                    </>
                  ),
                },
                { titulo: 'Socio', celda: (r) => r.socio },
                {
                  titulo: 'Estado',
                  celda: (r) => (
                    <span className={comun.badges}>
                      <EstadoBadge entidad="reserva" estado={r.estado} />
                      {r.posicion_cola && <span className={comun.sub}>Puesto {r.posicion_cola} en la cola</span>}
                    </span>
                  ),
                },
                {
                  titulo: 'Fechas',
                  celda: (r) =>
                    r.estado === 'ASIGNADA' ? (
                      <>
                        Retirar hasta {fecha(r.fecha_limite)}
                        <span className={`${comun.sub} ${comun.mono}`}>{r.ejemplar_asignado}</span>
                      </>
                    ) : (
                      <>Pedida {fechaHora(r.fecha_solicitud)}</>
                    ),
                },
                {
                  titulo: '',
                  celda: (r) =>
                    (r.estado === 'PENDIENTE' || r.estado === 'ASIGNADA') && (
                      <Button tamano="chico" variante="ghost">Cancelar</Button>
                    ),
                },
              ]}
            />
          )}
        </Resultado>
      </Card>
    </>
  )
}
