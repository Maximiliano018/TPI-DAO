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
import { ESTADOS, TIPOS_DE_PRESTAMO } from '../../../utils/estados.js';
import { formatearFecha } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import EstadoBadge from '../components/EstadoBadge.jsx';
import { usePrestamos } from '../hooks/usePrestamos.js';

/**
 * Préstamos: el administrador ve todos, el bibliotecario los de su sede (como origen o destino)
 * y el socio los propios. El filtro por sede y por socio lo aplica el backend.
 */
export default function PrestamosPage() {
  const { tienePermiso } = useSesion();
  const esPersonal = tienePermiso(PERMISOS.PRESTAMO_LEER);
  const titulo = esPersonal ? 'Préstamos' : 'Mis préstamos';
  useTituloDePagina(titulo);
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const { data, isPending, error, refetch } = usePrestamos({
    estado: filtros.estado,
    tipo: filtros.tipo,
    numero: filtros.numero,
    page,
    size,
  });

  const columnas = [
    {
      clave: 'numero',
      titulo: 'Número',
      render: (p) => (
        <Link to={`/prestamos/${p.id}`} className="mono">
          {p.numero}
        </Link>
      ),
    },
    { clave: 'libro', titulo: 'Libro' },
    ...(esPersonal ? [{ clave: 'socio', titulo: 'Socio' }] : []),
    { clave: 'tipo', titulo: 'Tipo', render: (p) => TIPOS_DE_PRESTAMO[p.tipo] },
    { clave: 'sede_destino', titulo: 'Retira en' },
    {
      clave: 'vence',
      titulo: 'Vence',
      render: (p) => (p.fecha_vencimiento ? formatearFecha(p.fecha_vencimiento) : '—'),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      render: (p) => <EstadoBadge entidad="prestamo" estado={p.estado} />,
    },
  ];

  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion={
          esPersonal
            ? 'Préstamos locales y entre sedes de su sede (o de toda la red).'
            : 'Sus préstamos, con el vencimiento y el estado del envío.'
        }
        acciones={
          tienePermiso(PERMISOS.PRESTAMO_REGISTRAR) && (
            <Button to="/prestamos/nuevo">Nuevo préstamo</Button>
          )
        }
      />
      <FilterBar etiqueta="Filtros de préstamos" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <BusquedaConEspera
          etiqueta="Buscar por número"
          valor={filtros.numero ?? ''}
          onBuscar={(numero) => cambiar({ numero })}
        />
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todos</option>
          {Object.entries(ESTADOS.prestamo).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Tipo"
          valor={filtros.tipo ?? ''}
          onCambiar={(tipo) => cambiar({ tipo })}
        >
          <option value="">Todos</option>
          {Object.entries(TIPOS_DE_PRESTAMO).map(([valor, texto]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && <EmptyState titulo="No hay préstamos que coincidan" />}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Préstamos" columnas={columnas} filas={data.items} idDe={(p) => p.id} />
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
