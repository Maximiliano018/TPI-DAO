import { useState } from 'react'
import {
  useEnviosExitosos,
  useLibrosMasSolicitados,
  useMovimientoSedes,
  useVencidosMultas,
} from '../../api/consultas'
import { useTieneRol } from '../../auth/contexto'
import { ATENCION } from '../../auth/permisos'
import { Badge } from '../../components/Badge/Badge'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { Grid } from '../../components/Grid/Grid'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { StatCard } from '../../components/StatCard/StatCard'
import { Table } from '../../components/Table/Table'
import { useAlcance } from '../comun/alcance'
import comun from '../comun/comun.module.css'
import { dias, fecha, numero, plural, pesos } from '../comun/formato'
import styles from './ReportesPage.module.css'

export function ReportesPage() {
  const [periodo, setPeriodo] = useState({ desde: '', hasta: '' })
  const alcance = useAlcance()
  // Logística ve los reportes logísticos (R1, R2); los de préstamos (R3, R4) son de atención.
  const veCirculacion = useTieneRol(...ATENCION)

  return (
    <>
      <PageHeader
        titulo="Reportes"
        descripcion={`Indicadores de ${veCirculacion ? 'préstamos y ' : ''}logística de ${alcance}.`}
      />

      <div className={comun.filtros}>
        <Field etiqueta="Desde">
          <input
            className={claseControl}
            type="date"
            value={periodo.desde}
            onChange={(e) => setPeriodo({ ...periodo, desde: e.target.value })}
          />
        </Field>
        <Field etiqueta="Hasta">
          <input
            className={claseControl}
            type="date"
            value={periodo.hasta}
            onChange={(e) => setPeriodo({ ...periodo, hasta: e.target.value })}
          />
        </Field>
        <span className={comun.sub}>
          {veCirculacion
            ? 'El período aplica a los tres primeros reportes.'
            : 'El período aplica a los dos reportes.'}
        </span>
      </div>

      <MovimientoEntreSedes periodo={periodo} />
      <Grid columna="ancha">
        <EnviosExitosos periodo={periodo} />
        {veCirculacion && <LibrosMasSolicitados periodo={periodo} />}
      </Grid>
      {veCirculacion && <VencidosYMultas />}
    </>
  )
}

type Periodo = { desde: string; hasta: string }

function MovimientoEntreSedes({ periodo }: { periodo: Periodo }) {
  const reporte = useMovimientoSedes(periodo)

  return (
    <Card
      titulo="Movimiento entre sedes"
      descripcion="Envíos por recorrido y tiempo promedio de tránsito (de despacho a recepción)."
      sinRelleno
    >
      <Resultado consulta={reporte}>
        {(r) => (
          <>
            <p className={styles.resumen}>
              {plural(r.envios_totales, 'envío')} en total · promedio general{' '}
              {r.dias_promedio_transito === null ? '—' : `${numero(r.dias_promedio_transito)} días`}
            </p>
            <Table
              filas={r.rutas}
              clave={(ruta) => `${ruta.sede_origen}-${ruta.sede_destino}`}
              vacio="No hubo envíos en el período."
              columnas={[
                {
                  titulo: 'Recorrido',
                  celda: (ruta) => (
                    <span className={comun.sinCorte}>
                      {ruta.sede_origen} → {ruta.sede_destino}
                    </span>
                  ),
                },
                { titulo: 'Envíos', alinear: 'derecha', celda: (ruta) => ruta.envios },
                { titulo: 'Recibidos', alinear: 'derecha', celda: (ruta) => ruta.recibidos },
                { titulo: 'En curso', alinear: 'derecha', celda: (ruta) => ruta.en_curso },
                { titulo: 'Extraviados', alinear: 'derecha', celda: (ruta) => ruta.extraviados },
                {
                  titulo: 'Tránsito promedio',
                  alinear: 'derecha',
                  celda: (ruta) =>
                    ruta.dias_promedio_transito === null ? '—' : `${numero(ruta.dias_promedio_transito)} días`,
                },
              ]}
            />
          </>
        )}
      </Resultado>
    </Card>
  )
}

function EnviosExitosos({ periodo }: { periodo: Periodo }) {
  const reporte = useEnviosExitosos(periodo)

  return (
    <Card
      titulo="Envíos exitosos e incidencias"
      descripcion="Sobre envíos finalizados: exitoso es el recibido conforme."
      sinRelleno
    >
      <Resultado consulta={reporte}>
        {(r) => (
          <>
            <div className={styles.cifras}>
              <StatCard
                etiqueta={`Tasa de éxito (${r.exitosos} de ${r.total})`}
                valor={r.tasa_exito === null ? '—' : `${numero(r.tasa_exito)} %`}
              />
              <div className={styles.incidencias}>
                <Badge variante="advertencia">{plural(r.incidencias.danados, 'dañado')}</Badge>
                <Badge variante="peligro">{plural(r.incidencias.destruidos, 'destruido')}</Badge>
                <Badge variante="peligro">{plural(r.incidencias.extraviados, 'extraviado')}</Badge>
              </div>
            </div>
            <Table
              filas={r.por_sede}
              clave={(s) => s.sede_id}
              vacio="No hay envíos finalizados en el período."
              columnas={[
                { titulo: 'Sede de origen', celda: (s) => s.sede },
                { titulo: 'Envíos', alinear: 'derecha', celda: (s) => s.total },
                { titulo: 'Incidencias', alinear: 'derecha', celda: (s) => s.incidencias },
                {
                  titulo: 'Éxito',
                  alinear: 'derecha',
                  celda: (s) => (s.tasa_exito === null ? '—' : `${numero(s.tasa_exito)} %`),
                },
              ]}
            />
          </>
        )}
      </Resultado>
    </Card>
  )
}

function LibrosMasSolicitados({ periodo }: { periodo: Periodo }) {
  const reporte = useLibrosMasSolicitados(periodo)

  return (
    <Card
      titulo="Libros más pedidos entre sedes"
      descripcion="Préstamos interbibliotecarios solicitados por libro."
      sinRelleno
    >
      <Resultado consulta={reporte}>
        {(libros) => (
          <Table
            filas={libros}
            clave={(l) => l.libro_id}
            vacio="No hubo préstamos inter-sedes en el período."
            columnas={[
              { titulo: '#', celda: (l) => libros.indexOf(l) + 1 },
              { titulo: 'Libro', celda: (l) => l.titulo },
              { titulo: 'Pedidos', alinear: 'derecha', celda: (l) => l.solicitudes },
              { titulo: 'Socios', alinear: 'derecha', celda: (l) => l.socios },
            ]}
          />
        )}
      </Resultado>
    </Card>
  )
}

function VencidosYMultas() {
  const reporte = useVencidosMultas()

  return (
    <Card
      titulo="Préstamos vencidos y multas"
      descripcion="Situación al día de hoy."
      sinRelleno
    >
      <Resultado consulta={reporte}>
        {(r) => (
          <>
            <p className={styles.resumen}>
              Multas pendientes: <strong>{pesos(r.total_pendiente)}</strong> · Ya saldadas:{' '}
              {pesos(r.total_saldado)}
            </p>
            <Grid columna="ancha">
              <Table
                filas={r.vencidos}
                clave={(v) => v.id}
                vacio="No hay préstamos vencidos."
                columnas={[
                  {
                    titulo: 'Préstamo vencido',
                    celda: (v) => (
                      <>
                        {v.socio}
                        <span className={comun.sub}>
                          {v.titulo} · {v.sede}
                        </span>
                      </>
                    ),
                  },
                  { titulo: 'Venció', celda: (v) => fecha(v.fecha_vencimiento) },
                  {
                    titulo: 'Atraso',
                    celda: (v) => <Badge variante="peligro">{dias(v.dias_atraso)}</Badge>,
                  },
                ]}
              />
              <Table
                filas={r.multas_por_socio}
                clave={(s) => s.socio_id}
                vacio="No hay multas."
                columnas={[
                  { titulo: 'Socio con multas', celda: (s) => s.socio },
                  { titulo: 'Pendiente', alinear: 'derecha', celda: (s) => pesos(s.pendiente) },
                  { titulo: 'Saldado', alinear: 'derecha', celda: (s) => pesos(s.saldado) },
                ]}
              />
            </Grid>
          </>
        )}
      </Resultado>
    </Card>
  )
}
