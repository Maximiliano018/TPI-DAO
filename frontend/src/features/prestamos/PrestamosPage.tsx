import { useState } from 'react'
import { usePrestamos } from '../../api/consultas'
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
import { dias, fecha } from '../comun/formato'

export function PrestamosPage() {
  // Entregar y devolver se registran en la sede destino (ARCHITECTURE.md §6.1).
  const operaEn = useOperaEnSede()
  const [soloAbiertos, setSoloAbiertos] = useState(true)
  const prestamos = usePrestamos(soloAbiertos)

  return (
    <>
      <PageHeader
        titulo="Préstamos"
        descripcion="Préstamos locales e interbibliotecarios."
        acciones={<Button>Nuevo préstamo</Button>}
      />

      <div className={comun.filtros}>
        <Field etiqueta="Mostrar">
          <select
            className={claseControl}
            value={soloAbiertos ? 'abiertos' : 'todos'}
            onChange={(e) => setSoloAbiertos(e.target.value === 'abiertos')}
          >
            <option value="abiertos">En curso (en envío, listos y activos)</option>
            <option value="todos">Todos, incluidos los cerrados</option>
          </select>
        </Field>
      </div>

      <Card sinRelleno>
        <Resultado consulta={prestamos}>
          {(lista) => (
            <Table
              filas={lista}
              clave={(p) => p.id}
              columnas={[
                {
                  titulo: 'Socio',
                  celda: (p) => (
                    <>
                      {p.socio}
                      <span className={comun.sub}>Socio nº {p.numero_socio}</span>
                    </>
                  ),
                },
                {
                  titulo: 'Libro',
                  celda: (p) => (
                    <>
                      {p.titulo}
                      <span className={`${comun.sub} ${comun.mono}`}>{p.codigo_inventario}</span>
                    </>
                  ),
                },
                {
                  titulo: 'Tipo',
                  celda: (p) =>
                    p.tipo === 'LOCAL' ? (
                      <>
                        Local<span className={comun.sub}>{p.sede_destino}</span>
                      </>
                    ) : (
                      <>
                        Inter-sedes
                        <span className={comun.sub}>
                          {p.sede_origen} → {p.sede_destino}
                        </span>
                      </>
                    ),
                },
                {
                  titulo: 'Estado',
                  celda: (p) => (
                    <span className={comun.badges}>
                      <EstadoBadge entidad="prestamo" estado={p.estado} />
                      {p.vencido && <Badge variante="peligro">Vencido · {dias(p.dias_atraso)}</Badge>}
                      {p.retiro_vencido && <Badge variante="peligro">Retiro vencido</Badge>}
                    </span>
                  ),
                },
                {
                  titulo: 'Fechas',
                  celda: (p) =>
                    p.estado === 'LISTO_PARA_RETIRO' ? (
                      <>
                        Retirar hasta {fecha(p.fecha_limite_retiro)}
                      </>
                    ) : p.fecha_vencimiento ? (
                      <>
                        Vence {fecha(p.fecha_vencimiento)}
                        <span className={comun.sub}>Desde {fecha(p.fecha_inicio)}</span>
                      </>
                    ) : (
                      <>Pedido {fecha(p.fecha_solicitud)}</>
                    ),
                },
                {
                  titulo: '',
                  celda: (p) =>
                    !operaEn(p.sede_destino_id) ? null : p.estado === 'LISTO_PARA_RETIRO' ? (
                      <Button tamano="chico" variante="secondary">Entregar</Button>
                    ) : p.estado === 'ACTIVO' ? (
                      <Button tamano="chico" variante="secondary">Devolver</Button>
                    ) : null,
                },
              ]}
            />
          )}
        </Resultado>
      </Card>
    </>
  )
}
