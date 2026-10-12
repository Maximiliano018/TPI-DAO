import { useState } from 'react'
import { useDisponibilidad, useSedes } from '../../api/consultas'
import type { DisponibilidadSede } from '../../api/tipos'
import { Badge } from '../../components/Badge/Badge'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'

export function DisponibilidadPage() {
  const [buscar, setBuscar] = useState('')
  const disponibilidad = useDisponibilidad(buscar)
  const sedes = useSedes()

  return (
    <>
      <PageHeader
        titulo="Disponibilidad"
        descripcion="Cuántos ejemplares de cada libro se pueden prestar hoy en cada sede."
      />

      <div className={comun.filtros}>
        <Field etiqueta="Buscar libro">
          <input
            className={claseControl}
            type="search"
            placeholder="Título o ISBN"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
          />
        </Field>
      </div>

      <Card sinRelleno>
        <Resultado consulta={disponibilidad}>
          {(libros) => (
            <Table
              filas={libros}
              clave={(l) => l.libro_id}
              vacio="Ningún libro coincide con la búsqueda."
              columnas={[
                {
                  titulo: 'Libro',
                  celda: (l) => (
                    <>
                      {l.titulo}
                      <span className={`${comun.sub} ${comun.mono}`}>{l.isbn}</span>
                    </>
                  ),
                },
                // Una columna por sede de la red.
                ...(sedes.data ?? []).map((s) => ({
                  titulo: s.nombre,
                  celda: (l: (typeof libros)[number]) => (
                    <CeldaSede detalle={l.sedes.find((d) => d.sede_id === s.id)} />
                  ),
                })),
              ]}
            />
          )}
        </Resultado>
      </Card>
    </>
  )
}

function CeldaSede({ detalle }: { detalle?: DisponibilidadSede }) {
  if (!detalle) return <span className={comun.sub}>Sin ejemplares</span>
  if (detalle.consulta_en_sala === detalle.total) return <Badge>Consulta en sala</Badge>

  const ocupados = [
    detalle.prestados && `${detalle.prestados} prestado(s)`,
    detalle.reservados && `${detalle.reservados} reservado(s)`,
    detalle.en_transito && `${detalle.en_transito} en tránsito`,
    detalle.en_revision && `${detalle.en_revision} en revisión`,
  ].filter(Boolean)

  return (
    <>
      <Badge variante={detalle.disponibles > 0 ? 'exito' : 'neutral'}>
        {detalle.disponibles} disponible{detalle.disponibles === 1 ? '' : 's'}
      </Badge>
      {ocupados.length > 0 && <span className={comun.sub}>{ocupados.join(' · ')}</span>}
    </>
  )
}
