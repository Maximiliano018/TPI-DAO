import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  BusquedaConEspera,
  Button,
  Card,
  Combobox,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  Table,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_FISICOS } from '../../../utils/estados.js';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoSocioBadge from '../../socios/components/EstadoSocioBadge.jsx';
import { useSocios } from '../../socios/hooks/useSocios.js';
import { useEjemplares, useLibros } from '../../catalogo/hooks/useCatalogo.js';
import { useRegistrarPrestamo } from '../hooks/usePrestamos.js';

/** Paso 1: buscar al socio por número, documento o nombre. */
function ElegirSocio({ elegido, onElegir }) {
  const [q, setQ] = useState('');
  const { data, isFetching } = useSocios({ q, size: 10 }, { enabled: q.length > 1 });
  if (elegido) {
    return (
      <p style={{ margin: 0 }}>
        {elegido.apellido}, {elegido.nombre} <span className="mono">{elegido.numero_socio}</span>{' '}
        <EstadoSocioBadge socio={elegido} />{' '}
        <Button variante="secondary" tamano="sm" onClick={() => onElegir(null)}>
          Cambiar
        </Button>
      </p>
    );
  }
  const columnas = [
    { clave: 'numero_socio', titulo: 'Número' },
    { clave: 'nombre', titulo: 'Socio', render: (s) => `${s.apellido}, ${s.nombre}` },
    { clave: 'documento', titulo: 'Documento', render: (s) => s.nro_documento },
    { clave: 'estado', titulo: 'Estado', render: (s) => <EstadoSocioBadge socio={s} /> },
    {
      clave: 'elegir',
      titulo: 'Acción',
      render: (s) => (
        <Button tamano="sm" variante="secondary" onClick={() => onElegir(s)}>
          Elegir
        </Button>
      ),
    },
  ];
  return (
    <>
      <BusquedaConEspera
        etiqueta="Buscar socio por número, documento o nombre"
        valor={q}
        onBuscar={setQ}
      />
      {isFetching && <Skeleton alto={48} />}
      {data && data.items.length === 0 && <p>No hay socios que coincidan.</p>}
      {data && data.items.length > 0 && (
        <Table
          etiqueta="Socios encontrados"
          columnas={columnas}
          filas={data.items}
          idDe={(s) => s.id}
        />
      )}
    </>
  );
}

/** Paso 2: el libro y un ejemplar disponible (de su sede: local; de otra: entre sedes). */
function ElegirEjemplar({ sedeId, elegido, onElegir }) {
  const libros = useLibros({ size: 100 });
  const [libroId, setLibroId] = useState('');
  const ejemplares = useEjemplares(
    { libro_id: libroId, estado: 'DISPONIBLE', size: 100 },
    { enabled: libroId !== '' },
  );
  if (libros.isPending) return <Skeleton alto={48} />;
  if (libros.error) return <ErrorState error={libros.error} onReintentar={libros.refetch} />;
  const disponibles = [...(ejemplares.data?.items ?? [])].sort(
    (a, b) => Number(b.sede_propietaria_id === sedeId) - Number(a.sede_propietaria_id === sedeId),
  );
  const columnas = [
    {
      clave: 'codigo',
      titulo: 'Código',
      render: (e) => <span className="mono">{e.codigo_inventario}</span>,
    },
    { clave: 'sede_propietaria', titulo: 'Sede' },
    {
      clave: 'estado_fisico',
      titulo: 'Estado físico',
      render: (e) => ESTADOS_FISICOS[e.estado_fisico],
    },
    {
      clave: 'tipo',
      titulo: 'Préstamo',
      render: (e) => (e.sede_propietaria_id === sedeId ? 'Local' : 'Entre sedes'),
    },
    {
      clave: 'elegir',
      titulo: 'Acción',
      render: (e) => (
        <Button
          tamano="sm"
          variante={elegido?.id === e.id ? 'primary' : 'secondary'}
          aria-pressed={elegido?.id === e.id}
          onClick={() => onElegir(e)}
        >
          {elegido?.id === e.id ? 'Elegido' : 'Elegir'}
        </Button>
      ),
    },
  ];
  return (
    <>
      <Combobox
        etiqueta="Libro"
        opciones={libros.data.items.map((lb) => ({
          id: lb.id,
          texto: lb.titulo,
          detalle: lb.autores.join(', '),
        }))}
        valor={libroId}
        onCambiar={(id) => {
          setLibroId(id);
          onElegir(null);
        }}
      />
      {ejemplares.isFetching && <Skeleton alto={48} />}
      {libroId !== '' && ejemplares.data && disponibles.length === 0 && (
        <EmptyState titulo="No hay ejemplares disponibles en la red">
          <p style={{ margin: 0 }}>
            El socio puede reservar el libro para retirarlo cuando se libere.
          </p>
        </EmptyState>
      )}
      {disponibles.length > 0 && (
        <Table
          etiqueta="Ejemplares disponibles"
          columnas={columnas}
          filas={disponibles}
          idDe={(e) => e.id}
        />
      )}
    </>
  );
}

/**
 * Registrar un préstamo en nombre del socio (en mostrador). Si el ejemplar es de esta sede el
 * préstamo es local; si es de otra, entre sedes: la sede origen arma el envío.
 */
export default function NuevoPrestamoPage() {
  useTituloDePagina('Nuevo préstamo');
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const registrar = useRegistrarPrestamo();
  const [socio, setSocio] = useState(null);
  const [ejemplar, setEjemplar] = useState(null);
  const [fallo, setFallo] = useState(null);
  const migas = [{ texto: 'Préstamos', to: '/prestamos' }, { texto: 'Nuevo préstamo' }];

  function confirmar() {
    setFallo(null);
    registrar.mutate(
      { socio_id: socio.id, ejemplar_id: ejemplar.id },
      {
        onSuccess: (prestamo) => {
          mostrar(`Préstamo ${prestamo.numero} registrado`);
          navegar(`/prestamos/${prestamo.id}`);
        },
        onError: setFallo,
      },
    );
  }

  return (
    <>
      <PageHeader
        titulo="Nuevo préstamo"
        descripcion={`El socio retira y devuelve en ${usuario.sede?.nombre ?? 'su sede'}.`}
        migas={<Breadcrumb items={migas} />}
      />
      <div className={inicio.pagina}>
        {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
        <Card titulo="1. Socio">
          <ElegirSocio elegido={socio} onElegir={setSocio} />
          {socio && socio.estado !== 'HABILITADO' && (
            <Alert tono="warning">
              El socio no está habilitado: el sistema va a rechazar el préstamo.
            </Alert>
          )}
        </Card>
        <Card titulo="2. Libro y ejemplar">
          <ElegirEjemplar sedeId={usuario.sede_id} elegido={ejemplar} onElegir={setEjemplar} />
        </Card>
        <div>
          <Button disabled={!socio || !ejemplar} cargando={registrar.isPending} onClick={confirmar}>
            Registrar préstamo
          </Button>
        </div>
      </div>
    </>
  );
}
