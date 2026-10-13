import { useState } from 'react'
import { useEjemplares, useLibros } from '../../api/consultas'
import type { Libro } from '../../api/tipos'
import { ATENCION } from '../../auth/permisos'
import { useTieneRol } from '../../auth/contexto'
import { Badge } from '../../components/Badge/Badge'
import { Button } from '../../components/Button/Button'
import { Card } from '../../components/Card/Card'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import { Modal } from '../../components/Modal/Modal'
import { PageHeader } from '../../components/PageHeader/PageHeader'
import { Resultado } from '../../components/Resultado/Resultado'
import { Table } from '../../components/Table/Table'
import comun from '../comun/comun.module.css'
import { EstadoBadge } from '../comun/EstadoBadge'
import { EliminarLibro } from './EliminarLibro'
import { NuevoLibroForm } from './NuevoLibroForm'

export function CatalogoPage() {
  const [buscar, setBuscar] = useState('')
  const [seleccionado, setSeleccionado] = useState<Libro | null>(null)
  const [modal, setModal] = useState<'nuevo' | 'eliminar' | null>(null)
  const libros = useLibros(buscar)
  const mantieneCatalogo = useTieneRol(...ATENCION)

  return (
    <>
      <PageHeader
        titulo="Catálogo"
        descripcion="Libros (obras) de la red y sus ejemplares físicos en cada sede. Elegí un libro para ver sus ejemplares."
        acciones={
          mantieneCatalogo && (
            <>
              <Button variante="secondary">Nuevo ejemplar</Button>
              <Button onClick={() => setModal('nuevo')}>Nuevo libro</Button>
            </>
          )
        }
      />

      <Modal titulo="Nuevo libro" abierto={modal === 'nuevo'} alCerrar={() => setModal(null)}>
        <NuevoLibroForm alTerminar={() => setModal(null)} />
      </Modal>

      {seleccionado && (
        <Modal
          titulo="Eliminar libro"
          abierto={modal === 'eliminar'}
          alCerrar={() => setModal(null)}
        >
          <EliminarLibro
            libro={seleccionado}
            alTerminar={(eliminado) => {
              setModal(null)
              if (eliminado) setSeleccionado(null)
            }}
          />
        </Modal>
      )}

      <div className={comun.filtros}>
        <Field etiqueta="Buscar">
          <input
            className={claseControl}
            type="search"
            placeholder="Título, autor o ISBN"
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
          />
        </Field>
      </div>

      <div className={comun.listadoDetalle}>
        <Card sinRelleno>
          <Resultado consulta={libros}>
            {(lista) => (
              <Table
                filas={lista}
                clave={(l) => l.id}
                alSeleccionar={setSeleccionado}
                seleccionada={seleccionado?.id}
                vacio="Ningún libro coincide con la búsqueda."
                columnas={[
                  {
                    titulo: 'Libro',
                    celda: (l) => (
                      <>
                        {l.titulo}
                        <span className={comun.sub}>
                          {l.autores.join(', ')}
                          {l.anio_publicacion && ` · ${l.anio_publicacion}`}
                        </span>
                      </>
                    ),
                  },
                  { titulo: 'Categoría', celda: (l) => l.categoria ?? '—' },
                  { titulo: 'ISBN', celda: (l) => <span className={comun.mono}>{l.isbn}</span> },
                  {
                    titulo: 'Disponibles',
                    alinear: 'derecha',
                    celda: (l) => `${l.disponibles} de ${l.ejemplares}`,
                  },
                ]}
              />
            )}
          </Resultado>
        </Card>

        <Card
          titulo="Ejemplares"
          descripcion={seleccionado?.titulo}
          sinRelleno={Boolean(seleccionado)}
          acciones={
            seleccionado &&
            mantieneCatalogo && (
              <Button tamano="chico" variante="ghost" onClick={() => setModal('eliminar')}>
                Eliminar libro
              </Button>
            )
          }
        >
          {seleccionado ? (
            <EjemplaresDeLibro libroId={seleccionado.id} />
          ) : (
            <p className={comun.sub}>Elegí un libro de la lista para ver sus copias físicas.</p>
          )}
        </Card>
      </div>
    </>
  )
}

function EjemplaresDeLibro({ libroId }: { libroId: number }) {
  const ejemplares = useEjemplares(libroId)

  return (
    <Resultado consulta={ejemplares}>
      {(lista) => (
        <Table
          filas={lista}
          clave={(e) => e.id}
          columnas={[
            {
              titulo: 'Código',
              celda: (e) => (
                <>
                  <span className={comun.mono}>{e.codigo_inventario}</span>
                  <span className={comun.sub}>{e.sede}</span>
                </>
              ),
            },
            {
              titulo: 'Estado y condición',
              celda: (e) => (
                <span className={comun.badges}>
                  <EstadoBadge entidad="ejemplar" estado={e.estado} />
                  <EstadoBadge entidad="condicion" estado={e.condicion_fisica} />
                  {!e.prestable && <Badge>Consulta en sala</Badge>}
                </span>
              ),
            },
          ]}
        />
      )}
    </Resultado>
  )
}
