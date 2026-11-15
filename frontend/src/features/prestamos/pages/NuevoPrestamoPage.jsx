import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
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
import ElegirSocio from '../../socios/components/ElegirSocio.jsx';
import SelectorDeLibro from '../../catalogo/components/SelectorDeLibro.jsx';
import { useEjemplares } from '../../catalogo/hooks/useCatalogo.js';
import { useRegistrarPrestamo } from '../hooks/usePrestamos.js';
import SedeDeOperacion, { useSedeDeOperacion } from '../../sedes/components/SedeDeOperacion.jsx';

/**
 * Paso 2: el libro (buscado en todo el catálogo) y un ejemplar disponible: de su sede, local;
 * de otra, entre sedes.
 */
function ElegirEjemplar({ sedeId, elegido, onElegir }) {
  const [libroId, setLibroId] = useState('');
  const ejemplares = useEjemplares(
    { libro_id: libroId, estado: 'DISPONIBLE', size: 100 },
    { enabled: libroId !== '' },
  );
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
      <SelectorDeLibro
        requerido={false}
        valor={libroId === '' ? undefined : libroId}
        onCambiar={(id) => {
          setLibroId(id ?? '');
          onElegir(null);
        }}
      />
      {ejemplares.error && (
        <ErrorState error={ejemplares.error} onReintentar={ejemplares.refetch} />
      )}
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
 * préstamo es local; si es de otra, entre sedes: la sede origen arma el envío. El administrador
 * elige la sede donde el socio lo retira.
 */
export default function NuevoPrestamoPage() {
  useTituloDePagina('Nuevo préstamo');
  const sede = useSedeDeOperacion();
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
      {
        socio_id: socio.id,
        ejemplar_id: ejemplar.id,
        ...(sede.esAdmin && { sede_destino_id: sede.sedeId }),
      },
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
        descripcion={
          sede.esAdmin && !sede.sedeId
            ? 'Elija la sede donde el socio retira y devuelve el libro.'
            : `El socio retira y devuelve en ${sede.nombre ?? 'su sede'}.`
        }
        migas={<Breadcrumb items={migas} />}
      />
      <div className={inicio.pagina}>
        {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
        <SedeDeOperacion
          control={sede}
          titulo="Sede de retiro"
          etiqueta="Sede donde el socio retira el libro"
          onCambiar={() => setEjemplar(null)}
        />
        <Card titulo="1. Socio">
          <ElegirSocio elegido={socio} onElegir={setSocio} />
          {socio && socio.estado !== 'HABILITADO' && (
            <Alert tono="warning">
              El socio no está habilitado: el sistema va a rechazar el préstamo.
            </Alert>
          )}
        </Card>
        <Card titulo="2. Libro y ejemplar">
          {sede.sedeId ? (
            <ElegirEjemplar sedeId={sede.sedeId} elegido={ejemplar} onElegir={setEjemplar} />
          ) : (
            <p style={{ margin: 0 }}>Primero elija la sede de retiro.</p>
          )}
        </Card>
        <div>
          <Button
            disabled={!socio || !ejemplar || !sede.sedeId}
            cargando={registrar.isPending}
            onClick={confirmar}
          >
            Registrar préstamo
          </Button>
        </div>
      </div>
    </>
  );
}
