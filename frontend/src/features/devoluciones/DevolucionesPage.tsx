import { useDevoluciones } from '../../api/consultas'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { EstadoBadge } from '../comun/EstadoBadge'
import { dias, fechaHora, pesos } from '../comun/formato'

export function DevolucionesPage() {
  const devoluciones = useDevoluciones()

  return (
    <>
      <PageHeader
        titulo="Devoluciones"
        descripcion="Devoluciones registradas, con el estado físico del material y la multa si hubo atraso."
        acciones={<Button>Registrar devolución</Button>}
      />

      <Card sinRelleno>
        <Resultado consulta={devoluciones}>
          {(lista) => (
            <Table
              filas={lista}
              clave={(d) => d.id}
              columnas={[
                {
                  titulo: 'Fecha',
                  celda: (d) => (
                    <>
                      {fechaHora(d.fecha_hora)}
                      <span className={comun.sub}>{d.sede}</span>
                    </>
                  ),
                },
                { titulo: 'Socio', celda: (d) => d.socio },
                {
                  titulo: 'Libro',
                  celda: (d) => (
                    <>
                      {d.titulo}
                      <span className={`${comun.sub} ${comun.mono}`}>{d.codigo_inventario}</span>
                    </>
                  ),
                },
                {
                  titulo: 'Estado físico',
                  celda: (d) => (
                    <>
                      <EstadoBadge entidad="condicion" estado={d.condicion_fisica} />
                      {d.observacion && <span className={comun.sub}>{d.observacion}</span>}
                    </>
                  ),
                },
                {
                  titulo: 'Multa',
                  celda: (d) =>
                    d.multa_estado ? (
                      <span className={comun.badges}>
                        {pesos(d.multa_monto)}
                        <EstadoBadge entidad="multa" estado={d.multa_estado} />
                        <span className={comun.sub}>{dias(d.dias_atraso ?? 0)} de atraso</span>
                      </span>
                    ) : (
                      <span className={comun.sub}>Sin atraso</span>
                    ),
                },
                { titulo: 'Registró', celda: (d) => d.registrado_por },
              ]}
            />
          )}
        </Resultado>
      </Card>
    </>
  )
}
