import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  BusquedaConEspera,
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroSelect,
  PageHeader,
  Pagination,
  Skeleton,
  Table,
} from '../../../components/index.js';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import EstadoSocioBadge from '../components/EstadoSocioBadge.jsx';
import { useSocios } from '../hooks/useSocios.js';

/** Búsqueda de socios por número, documento o nombre, con filtros en la URL. */
export default function SociosPage() {
  useTituloDePagina('Socios');
  const { tienePermiso } = useSesion();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const { data, isPending, error, refetch } = useSocios({
    q: filtros.q,
    estado: filtros.estado,
    page,
    size,
  });

  const columnas = [
    {
      clave: 'numero_socio',
      titulo: 'Número',
      render: (s) => <span className={estilos.codigo}>{s.numero_socio}</span>,
    },
    {
      clave: 'nombre',
      titulo: 'Socio',
      render: (s) => (
        <Link to={`/socios/${s.id}`}>
          {s.apellido}, {s.nombre}
        </Link>
      ),
    },
    {
      clave: 'documento',
      titulo: 'Documento',
      render: (s) => `${s.tipo_documento} ${s.nro_documento}`,
    },
    { clave: 'sede_alta', titulo: 'Sede de alta' },
    { clave: 'estado', titulo: 'Estado', render: (s) => <EstadoSocioBadge socio={s} /> },
  ];

  return (
    <>
      <PageHeader
        titulo="Socios"
        descripcion="Socios de la red: pueden pedir material en cualquier sede activa."
        acciones={
          tienePermiso(PERMISOS.SOCIO_REGISTRAR) && <Button to="/socios/nuevo">Nuevo socio</Button>
        }
      />
      <FilterBar etiqueta="Filtros de socios" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <BusquedaConEspera
          etiqueta="Buscar por número, documento o nombre"
          valor={filtros.q ?? ''}
          onBuscar={(q) => cambiar({ q })}
        />
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todos</option>
          <option value="HABILITADO">Habilitados</option>
          <option value="INHABILITADO">Inhabilitados</option>
          <option value="BAJA">Dados de baja</option>
        </FiltroSelect>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState titulo="No hay socios que coincidan">
          {hayFiltros && (
            <Button variante="secondary" onClick={limpiar}>
              Limpiar filtros
            </Button>
          )}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Socios" columnas={columnas} filas={data.items} idDe={(s) => s.id} />
          <Pagination
            page={data.page}
            size={data.size}
            total={data.total}
            onPage={(p) => cambiar({ page: p })}
            onSize={(s) => cambiar({ size: s === 20 ? '' : s })}
          />
        </>
      )}
    </>
  );
}
