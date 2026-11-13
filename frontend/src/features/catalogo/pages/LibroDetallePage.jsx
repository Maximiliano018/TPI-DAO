import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  Table,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { ESTADOS_FISICOS, TIPOS_DE_MATERIAL } from '../../../utils/estados.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoEjemplarBadge from '../components/EstadoEjemplarBadge.jsx';
import {
  useDisponibilidad,
  useEjemplares,
  useEliminarLibro,
  useLibro,
} from '../hooks/useCatalogo.js';

function Disponibilidad({ libroId }) {
  const { data, isPending, error, refetch } = useDisponibilidad(libroId);
  if (isPending) return <Skeleton alto={96} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  if (data.por_sede.length === 0) {
    return <p style={{ margin: 0 }}>No hay ejemplares en las sedes activas de la red.</p>;
  }
  const columnas = [
    { clave: 'sede', titulo: 'Sede' },
    { clave: 'disponibles', titulo: 'Disponibles' },
    { clave: 'prestados', titulo: 'Prestados' },
    { clave: 'reservados', titulo: 'Reservados' },
    { clave: 'en_transito', titulo: 'En tránsito' },
    { clave: 'totales', titulo: 'Total' },
  ];
  return (
    <>
      <p style={{ marginTop: 0 }}>
        {data.total_red.disponibles} de {data.total_red.totales} ejemplares disponibles en la red.
        {data.total_red.disponibles === 0 && ' Puede reservarlo para retirarlo cuando se libere.'}
      </p>
      <Table
        etiqueta="Disponibilidad por sede"
        columnas={columnas}
        filas={data.por_sede}
        idDe={(s) => s.sede_id}
      />
    </>
  );
}

function Ejemplares({ libroId }) {
  const { data, isPending, error, refetch } = useEjemplares({ libro_id: libroId, size: 100 });
  if (isPending) return <Skeleton alto={96} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  if (data.items.length === 0) return <EmptyState titulo="Todavía no hay ejemplares" />;
  const columnas = [
    {
      clave: 'codigo',
      titulo: 'Código',
      render: (e) => (
        <Link to={`/ejemplares/${e.id}`} className="mono">
          {e.codigo_inventario}
        </Link>
      ),
    },
    { clave: 'sede_propietaria', titulo: 'Sede' },
    {
      clave: 'estado_fisico',
      titulo: 'Estado físico',
      render: (e) => ESTADOS_FISICOS[e.estado_fisico],
    },
    {
      clave: 'estado',
      titulo: 'Disponibilidad',
      render: (e) => <EstadoEjemplarBadge estado={e.estado} />,
    },
  ];
  return <Table etiqueta="Ejemplares" columnas={columnas} filas={data.items} idDe={(e) => e.id} />;
}

function EliminarLibroDialog({ libro, onCerrar }) {
  const eliminar = useEliminarLibro();
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Eliminar «${libro.titulo}»`}
      descripcion="Solo se puede eliminar un libro cargado por error, sin ejemplares."
      textoConfirmar="Eliminar"
      peligro
      procesando={eliminar.isPending}
      onConfirmar={() =>
        eliminar.mutate(libro.id, {
          onSuccess: () => {
            mostrar('Libro eliminado');
            navegar('/catalogo');
          },
          onError: setFallo,
        })
      }
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** Ficha de un libro: datos, disponibilidad por sede y, para el personal, sus ejemplares. */
export default function LibroDetallePage() {
  const { id } = useParams();
  const { tienePermiso } = useSesion();
  const { data: libro, isPending, error, refetch } = useLibro(id);
  const [eliminando, setEliminando] = useState(false);
  useTituloDePagina(libro?.titulo ?? 'Libro');
  const migas = [{ texto: 'Catálogo', to: '/catalogo' }, { texto: libro?.titulo ?? 'Libro' }];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Libro" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
      </>
    );
  }

  const administra = tienePermiso(PERMISOS.CATALOGO_ADMINISTRAR);
  const gestionaEjemplares = tienePermiso(PERMISOS.EJEMPLAR_ADMINISTRAR);
  return (
    <>
      <PageHeader
        titulo={libro.titulo}
        descripcion={libro.autores.join(', ')}
        migas={<Breadcrumb items={migas} />}
        acciones={
          <>
            {gestionaEjemplares && (
              <Button to={`/ejemplares/nuevo?libro_id=${libro.id}`}>Agregar ejemplar</Button>
            )}
            {administra && (
              <Button to={`/catalogo/${libro.id}/editar`} variante="secondary">
                Editar
              </Button>
            )}
            {administra && libro.ejemplares === 0 && (
              <Button variante="danger" onClick={() => setEliminando(true)}>
                Eliminar
              </Button>
            )}
          </>
        }
      />
      <div className={inicio.pagina}>
        <div className={estilos.datos}>
          <Card titulo="Datos del libro">
            <dl className={estilos.definiciones}>
              <dt>ISBN</dt>
              <dd>{libro.isbn ?? 'Sin ISBN'}</dd>
              <dt>Editorial</dt>
              <dd>{libro.editorial ?? 'Sin dato'}</dd>
              <dt>Año de edición</dt>
              <dd>{libro.anio_edicion ?? 'Sin dato'}</dd>
              <dt>Categoría</dt>
              <dd>{libro.categoria.nombre}</dd>
              <dt>Tipo de material</dt>
              <dd>{TIPOS_DE_MATERIAL[libro.tipo_material]}</dd>
            </dl>
          </Card>
          <Card titulo="Disponibilidad por sede">
            <Disponibilidad libroId={libro.id} />
          </Card>
        </div>
        {tienePermiso(PERMISOS.EJEMPLAR_LEER) && (
          <Card titulo="Ejemplares">
            <Ejemplares libroId={libro.id} />
          </Card>
        )}
      </div>
      {eliminando && <EliminarLibroDialog libro={libro} onCerrar={() => setEliminando(false)} />}
    </>
  );
}
