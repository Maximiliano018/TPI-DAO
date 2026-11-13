import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  BusquedaConEspera,
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
import { ESTADOS, ESTADOS_FISICOS } from '../../../utils/estados.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import EstadoEjemplarBadge from '../components/EstadoEjemplarBadge.jsx';
import { useEjemplares } from '../hooks/useCatalogo.js';

/**
 * Ejemplares de la red. El bibliotecario ve por defecto los de su sede (propios o alojados);
 * puede quitar el filtro para buscar en toda la red.
 */
export default function EjemplaresPage() {
  useTituloDePagina('Ejemplares');
  const { usuario } = useSesion();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const sedeId = filtros.sede_id ?? (usuario.sede_id ? String(usuario.sede_id) : '');
  const sedes = useSedes({ estado: 'TODAS', orden: 'nombre', size: 100 });
  const { data, isPending, error, refetch } = useEjemplares({
    sede_id: sedeId === 'todas' ? undefined : sedeId,
    estado: filtros.estado,
    codigo: filtros.codigo,
    page,
    size,
  });

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
    { clave: 'libro', titulo: 'Libro' },
    { clave: 'sede_propietaria', titulo: 'Sede' },
    { clave: 'sede_actual', titulo: 'Está en' },
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

  return (
    <>
      <PageHeader
        titulo="Ejemplares"
        descripcion="Copias físicas de la red. Para cargar uno nuevo, abra el libro en el catálogo."
      />
      <FilterBar etiqueta="Filtros de ejemplares" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <BusquedaConEspera
          etiqueta="Buscar por código"
          valor={filtros.codigo ?? ''}
          onBuscar={(codigo) => cambiar({ codigo })}
        />
        <FiltroSelect
          etiqueta="Sede"
          valor={sedeId}
          onCambiar={(valor) => cambiar({ sede_id: valor || 'todas' })}
        >
          <option value="todas">Toda la red</option>
          {(sedes.data?.items ?? []).map((sede) => (
            <option key={sede.id} value={sede.id}>
              {sede.nombre}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Disponibilidad"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todas</option>
          {Object.entries(ESTADOS.ejemplar).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && <EmptyState titulo="No hay ejemplares que coincidan" />}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Ejemplares" columnas={columnas} filas={data.items} idDe={(e) => e.id} />
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
