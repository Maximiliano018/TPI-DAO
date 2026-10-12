import { useState } from 'react'
import { useSocios } from '../../api/consultas'
import { Badge } from '../../components/Badge/Badge'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { pesos } from '../comun/formato'

export function SociosPage() {
  const [buscar, setBuscar] = useState('')
  const socios = useSocios(buscar)

  return (
    <>
      <PageHeader
        titulo="Socios"
        descripcion="Socios de la red: pueden pedir préstamos en cualquier sede activa."
        acciones={<Button>Nuevo socio</Button>}
      />

      <div className={comun.filtros}>
        <Field etiqueta="Buscar">
          <input
            className={claseControl}
            type="search"
            placeholder="DNI, nº de socio o nombre"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
          />
        </Field>
      </div>

      <Card sinRelleno>
        <Resultado consulta={socios}>
          {(lista) => (
            <Table
              filas={lista}
              clave={(s) => s.id}
              vacio="Ningún socio coincide con la búsqueda."
              columnas={[
                { titulo: 'Nº', celda: (s) => <span className={comun.mono}>{s.numero_socio}</span> },
                {
                  titulo: 'Socio',
                  celda: (s) => (
                    <>
                      {s.apellido}, {s.nombre}
                      <span className={comun.sub}>DNI {s.dni}</span>
                    </>
                  ),
                },
                { titulo: 'Contacto', celda: (s) => s.email ?? '—' },
                { titulo: 'Préstamos en curso', alinear: 'derecha', celda: (s) => s.prestamos_abiertos },
                {
                  titulo: 'Multas pendientes',
                  alinear: 'derecha',
                  celda: (s) => (s.multas_pendientes ? pesos(s.multas_pendientes) : '—'),
                },
                {
                  titulo: 'Estado',
                  celda: (s) =>
                    s.habilitado ? (
                      <Badge variante="exito">Habilitado</Badge>
                    ) : (
                      <>
                        <Badge variante="peligro">Inhabilitado</Badge>
                        <span className={comun.sub}>{s.motivo_inhabilitacion}</span>
                      </>
                    ),
                },
                {
                  titulo: '',
                  celda: (s) => (
                    <span className={comun.acciones}>
                      <Button tamano="chico" variante="secondary">Editar</Button>
                      <Button tamano="chico" variante="ghost">
                        {s.habilitado ? 'Inhabilitar' : 'Habilitar'}
                      </Button>
                    </span>
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
