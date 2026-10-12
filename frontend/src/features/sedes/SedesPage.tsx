import { useSedes } from '../../api/consultas'
import type { Sede } from '../../api/tipos'
import { Badge } from '../../components/Badge/Badge'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { Grid } from '../../components/Grid/Grid'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import comun from '../comun/comun.module.css'
import { diaSemana, hora } from '../comun/formato'
import styles from './SedesPage.module.css'

export function SedesPage() {
  const sedes = useSedes()

  return (
    <>
      <PageHeader
        titulo="Sedes"
        descripcion="Sedes de la red: dirección, contacto, horarios y estado."
        acciones={<Button>Nueva sede</Button>}
      />

      <Resultado consulta={sedes}>
        {(lista) => (
          <Grid columna="ancha">
            {lista.map((s) => (
              <Card
                key={s.id}
                titulo={s.nombre}
                acciones={
                  s.activa ? <Badge variante="exito">Activa</Badge> : <Badge>Dada de baja</Badge>
                }
              >
                <dl className={styles.datos}>
                  <dt>Código</dt>
                  <dd className={comun.mono}>{s.codigo}</dd>
                  <dt>Dirección</dt>
                  <dd>
                    {s.direccion}, {s.localidad}
                  </dd>
                  <dt>Contacto</dt>
                  <dd>{[s.telefono, s.email].filter(Boolean).join(' · ') || '—'}</dd>
                  <dt>Ejemplares</dt>
                  <dd>{s.cantidad_ejemplares}</dd>
                  <dt>Horarios</dt>
                  <dd>
                    {agruparHorarios(s).map((linea) => (
                      <span key={linea} className={styles.horario}>
                        {linea}
                      </span>
                    ))}
                  </dd>
                </dl>
                <div className={styles.botones}>
                  <Button tamano="chico" variante="secondary">Editar</Button>
                  <Button tamano="chico" variante="ghost">
                    {s.activa ? 'Dar de baja' : 'Reactivar'}
                  </Button>
                </div>
              </Card>
            ))}
          </Grid>
        )}
      </Resultado>
    </>
  )
}

/** "Lun a Vie 08:00–12:00, 16:00–20:00": junta los días con las mismas franjas. */
function agruparHorarios(sede: Sede): string[] {
  const franjasPorDia = new Map<number, string[]>()
  for (const h of sede.horarios) {
    const franjas = franjasPorDia.get(h.dia_semana) ?? []
    franjas.push(`${hora(h.hora_apertura)}–${hora(h.hora_cierre)}`)
    franjasPorDia.set(h.dia_semana, franjas)
  }

  const grupos: { desde: number; hasta: number; franjas: string }[] = []
  for (const [dia, franjas] of franjasPorDia) {
    const texto = franjas.join(', ')
    const ultimo = grupos.at(-1)
    if (ultimo && ultimo.franjas === texto && ultimo.hasta === dia - 1) ultimo.hasta = dia
    else grupos.push({ desde: dia, hasta: dia, franjas: texto })
  }

  return grupos.map((g) =>
    g.desde === g.hasta
      ? `${diaSemana(g.desde)} ${g.franjas}`
      : `${diaSemana(g.desde)} a ${diaSemana(g.hasta)} ${g.franjas}`,
  )
}
