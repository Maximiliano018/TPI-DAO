import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../api/client'
import { useTablero } from '../../api/consultas'
import { Badge } from '../../components/Badge/Badge'
import { Card } from '../../components/Card/Card'
import { Grid } from '../../components/Grid/Grid'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { StatCard } from '../../components/StatCard/StatCard'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { EstadoBadge } from '../comun/EstadoBadge'
import { dias, fecha, fechaHora, pesos } from '../comun/formato'
import styles from './TableroPage.module.css'

export function TableroPage() {
  const tablero = useTablero()

  return (
    <>
      <PageHeader titulo="Tablero" descripcion="Resumen de la actividad de la red de bibliotecas." />

      <Resultado consulta={tablero}>
        {(t) => (
          <>
            <Grid>
              <StatCard etiqueta="Préstamos activos" valor={String(t.prestamos_activos)} />
              <StatCard etiqueta="Préstamos vencidos" valor={String(t.prestamos_vencidos)} />
              <StatCard etiqueta="Material en tránsito" valor={String(t.remitos_en_transito)} />
              <StatCard etiqueta="Listos para retiro" valor={String(t.listos_para_retiro)} />
              <StatCard etiqueta="Reservas en espera" valor={String(t.reservas_pendientes)} />
              <StatCard etiqueta="Multas pendientes" valor={pesos(t.multas_pendientes_monto)} />
            </Grid>

            {t.remitos_demorados > 0 && (
              <p className={styles.alerta}>
                ⚠ {t.remitos_demorados} remito(s) en tránsito superan el plazo máximo: revisar en
                Envíos.
              </p>
            )}

            <Grid columna="ancha">
              <Card titulo="Vencimientos" descripcion="Vencidos y que vencen en los próximos 7 días" sinRelleno>
                <Table
                  filas={t.proximos_vencimientos}
                  clave={(v) => v.id}
                  vacio="No hay vencimientos próximos."
                  columnas={[
                    {
                      titulo: 'Socio',
                      celda: (v) => (
                        <>
                          {v.socio}
                          <span className={comun.sub}>{v.titulo}</span>
                        </>
                      ),
                    },
                    { titulo: 'Vence', celda: (v) => fecha(v.fecha_vencimiento) },
                    {
                      titulo: 'Situación',
                      celda: (v) =>
                        v.dias_restantes < 0 ? (
                          <Badge variante="peligro">Vencido hace {dias(-v.dias_restantes)}</Badge>
                        ) : (
                          <Badge variante="advertencia">Faltan {dias(v.dias_restantes)}</Badge>
                        ),
                    },
                  ]}
                />
              </Card>

              <Card titulo="Últimos movimientos de remitos" sinRelleno>
                <Table
                  filas={t.ultimos_movimientos}
                  clave={(m) => m.id}
                  columnas={[
                    {
                      titulo: 'Remito',
                      celda: (m) => (
                        <>
                          <span className={comun.mono}>{m.numero}</span>
                          <span className={comun.sub}>{m.titulo}</span>
                        </>
                      ),
                    },
                    { titulo: 'Estado', celda: (m) => <EstadoBadge entidad="remito" estado={m.estado_nuevo} /> },
                    {
                      titulo: 'Cuándo',
                      celda: (m) => (
                        <>
                          {fechaHora(m.fecha_hora)}
                          <span className={comun.sub}>{m.usuario}</span>
                        </>
                      ),
                    },
                  ]}
                />
              </Card>
            </Grid>
          </>
        )}
      </Resultado>

      <EstadoConexion />
    </>
  )
}

type Health = { estado: string; base_de_datos: string }

/** Indicador de que el front se comunica con el backend. */
function EstadoConexion() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/health'),
  })

  if (health.isPending) return <p className={`${styles.estado} ${styles.info}`}>Conectando con el backend…</p>
  if (health.isError)
    return (
      <p className={`${styles.estado} ${styles.error}`}>
        Backend sin conexión ({health.error.message}). ¿Está corriendo en el puerto 8000?
      </p>
    )
  return <p className={`${styles.estado} ${styles.ok}`}>Backend conectado · base de datos OK</p>
}
