import { useState } from 'react'
import { useSedes } from '../../api/consultas'
import type { Sede } from '../../api/tipos'
import { useTieneRol } from '../../auth/contexto'
import { Badge } from '../../components/Badge/Badge'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { Grid } from '../../components/Grid/Grid'
import { Modal } from '../../components/Modal/Modal'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import comun from '../comun/comun.module.css'
import { diaSemana, fechaHora, hora } from '../comun/formato'
import { CambiarEstadoSede } from './CambiarEstadoSede'
import { HorariosForm } from './HorariosForm'
import { SedeForm } from './SedeForm'
import styles from './SedesPage.module.css'

type Dialogo =
  | { tipo: 'nueva' }
  | { tipo: 'editar' | 'horarios' | 'estado'; sede: Sede }
  | null

function tituloDe(dialogo: Dialogo): string {
  if (!dialogo) return ''
  if (dialogo.tipo === 'nueva') return 'Nueva sede'
  const { nombre, activa } = dialogo.sede
  if (dialogo.tipo === 'editar') return `Editar ${nombre}`
  if (dialogo.tipo === 'horarios') return `Horarios de ${nombre}`
  return activa ? 'Dar de baja la sede' : 'Reactivar la sede'
}

export function SedesPage() {
  const sedes = useSedes()
  // El ABM de sedes es del ADMIN; el resto del personal solo consulta.
  const esAdmin = useTieneRol('ADMIN')
  const [dialogo, setDialogo] = useState<Dialogo>(null)
  const cerrar = () => setDialogo(null)

  return (
    <>
      <PageHeader
        titulo="Sedes"
        descripcion="Sedes de la red: dirección, contacto, horarios y estado."
        acciones={
          esAdmin && <Button onClick={() => setDialogo({ tipo: 'nueva' })}>Nueva sede</Button>
        }
      />

      <Modal abierto={dialogo !== null} titulo={tituloDe(dialogo)} alCerrar={cerrar}>
        {dialogo?.tipo === 'nueva' && <SedeForm alTerminar={cerrar} />}
        {dialogo?.tipo === 'editar' && <SedeForm sede={dialogo.sede} alTerminar={cerrar} />}
        {dialogo?.tipo === 'horarios' && <HorariosForm sede={dialogo.sede} alTerminar={cerrar} />}
        {dialogo?.tipo === 'estado' && (
          <CambiarEstadoSede sede={dialogo.sede} alTerminar={cerrar} />
        )}
      </Modal>

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
                  {!s.activa && (
                    <>
                      <dt>Baja</dt>
                      <dd>{fechaHora(s.fecha_baja)}</dd>
                    </>
                  )}
                  <dt>Horarios</dt>
                  <dd>
                    {s.horarios.length === 0 && '—'}
                    {agruparHorarios(s).map((linea) => (
                      <span key={linea} className={styles.horario}>
                        {linea}
                      </span>
                    ))}
                  </dd>
                </dl>
                {esAdmin && (
                  <div className={styles.botones}>
                    <Button
                      tamano="chico"
                      variante="secondary"
                      onClick={() => setDialogo({ tipo: 'editar', sede: s })}
                    >
                      Editar
                    </Button>
                    <Button
                      tamano="chico"
                      variante="secondary"
                      onClick={() => setDialogo({ tipo: 'horarios', sede: s })}
                    >
                      Horarios
                    </Button>
                    <Button
                      tamano="chico"
                      variante="ghost"
                      onClick={() => setDialogo({ tipo: 'estado', sede: s })}
                    >
                      {s.activa ? 'Dar de baja' : 'Reactivar'}
                    </Button>
                  </div>
                )}
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
