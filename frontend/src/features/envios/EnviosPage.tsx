import { useState } from 'react'
import { useRemitos } from '../../api/consultas'
import type { EstadoRemito, Remito } from '../../api/tipos'
import { useOperaEnSede } from '../../auth/contexto'
import { Badge } from '../../components/Badge/Badge'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { EstadoBadge } from '../comun/EstadoBadge'
import { ESTADOS } from '../comun/estados'
import { fechaHora } from '../comun/formato'
import { RemitoTimeline } from './RemitoTimeline'

// Próxima acción de cada estado (patrón State del remito, ARCHITECTURE.md §4.4).
const SIGUIENTE_ACCION: Partial<Record<EstadoRemito, string>> = {
  GENERADO: 'Empaquetar',
  EMPAQUETADO: 'Despachar',
  EN_TRANSITO: 'Recibir',
}

export function EnviosPage() {
  // Empaquetar y despachar los hace la sede origen; recibir, la destino (ARCHITECTURE.md §6.1).
  const operaEn = useOperaEnSede()
  const puedeAvanzar = (r: Remito) =>
    r.estado === 'EN_TRANSITO' ? operaEn(r.sede_destino_id) : operaEn(r.sede_origen_id)
  const [estado, setEstado] = useState('')
  const [seleccionado, setSeleccionado] = useState<Remito | null>(null)
  const remitos = useRemitos(estado)

  return (
    <>
      <PageHeader
        titulo="Envíos"
        descripcion="Remitos entre sedes: empaquetar, despachar y recibir ejemplares. Elegí un remito para ver su trazabilidad."
      />

      <div className={comun.filtros}>
        <Field etiqueta="Estado">
          <select className={claseControl} value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(ESTADOS.remito).map(([valor, { texto }]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className={comun.listadoDetalle}>
        <Card sinRelleno>
          <Resultado consulta={remitos}>
            {(lista) => (
              <Table
                filas={lista}
                clave={(r) => r.id}
                alSeleccionar={setSeleccionado}
                seleccionada={seleccionado?.id}
                columnas={[
                  {
                    titulo: 'Remito',
                    celda: (r) => (
                      <>
                        <span className={comun.mono}>{r.numero}</span>
                        <span className={comun.sub}>{r.sentido === 'IDA' ? 'Ida' : 'Vuelta'}</span>
                      </>
                    ),
                  },
                  {
                    titulo: 'Libro',
                    celda: (r) => (
                      <>
                        {r.titulo}
                        <span className={`${comun.sub} ${comun.mono}`}>{r.codigo_inventario}</span>
                      </>
                    ),
                  },
                  {
                    titulo: 'Recorrido',
                    celda: (r) => (
                      <>
                        <span className={comun.sinCorte}>
                          {r.sede_origen} → {r.sede_destino}
                        </span>
                        <span className={comun.sub}>Generado {fechaHora(r.fecha_generacion)}</span>
                      </>
                    ),
                  },
                  {
                    titulo: 'Estado',
                    celda: (r) => (
                      <span className={comun.badges}>
                        <EstadoBadge entidad="remito" estado={r.estado} />
                        {r.resultado_revision && r.resultado_revision !== 'CONFORME' && (
                          <EstadoBadge entidad="revision" estado={r.resultado_revision} />
                        )}
                        {r.demorado && <Badge variante="advertencia">Demorado</Badge>}
                      </span>
                    ),
                  },
                  {
                    titulo: '',
                    celda: (r) =>
                      SIGUIENTE_ACCION[r.estado] &&
                      puedeAvanzar(r) && (
                        <Button tamano="chico" variante="secondary" onClick={(e) => e.stopPropagation()}>
                          {SIGUIENTE_ACCION[r.estado]}
                        </Button>
                      ),
                  },
                ]}
              />
            )}
          </Resultado>
        </Card>

        <Card
          titulo="Trazabilidad"
          descripcion={seleccionado ? `${seleccionado.numero} · ${seleccionado.titulo}` : undefined}
        >
          {seleccionado ? (
            <RemitoTimeline remito={seleccionado} />
          ) : (
            <p className={comun.sub}>Elegí un remito de la lista para ver por qué estados pasó.</p>
          )}
        </Card>
      </div>
    </>
  )
}
