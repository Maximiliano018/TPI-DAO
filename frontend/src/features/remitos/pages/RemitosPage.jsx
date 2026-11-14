import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Badge,
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
import { ESTADOS, MOTIVOS_DE_REMITO } from '../../../utils/estados.js';
import { formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import { useRemitos } from '../../prestamos/hooks/usePrestamos.js';

/** Remitos de la sede (como origen o destino); el administrador ve los de toda la red. */
export default function RemitosPage() {
  useTituloDePagina('Remitos');
  const { tienePermiso } = useSesion();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const { data, isPending, error, refetch } = useRemitos({
    estado: filtros.estado,
    motivo: filtros.motivo,
    numero: filtros.numero,
    abiertos: filtros.abiertos === 'si' ? true : undefined,
    atrasados: filtros.abiertos === 'atrasados' ? true : undefined,
    page,
    size,
  });

  const columnas = [
    {
      clave: 'numero',
      titulo: 'Número',
      render: (r) => (
        <Link to={`/remitos/${r.id}`} className="mono">
          {r.numero}
        </Link>
      ),
    },
    { clave: 'motivo', titulo: 'Motivo', render: (r) => MOTIVOS_DE_REMITO[r.motivo] },
    { clave: 'sede_origen', titulo: 'Desde' },
    { clave: 'sede_destino', titulo: 'Hacia' },
    { clave: 'lineas', titulo: 'Ejemplares', render: (r) => r.lineas.length },
    {
      clave: 'fecha',
      titulo: 'Generado',
      render: (r) => formatearFechaHora(r.fecha_generacion),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      render: (r) => (
        <>
          <EstadoBadge entidad="remito" estado={r.estado} />{' '}
          {r.atrasado && <Badge tono="danger">Atrasado</Badge>}
        </>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        titulo="Remitos"
        descripcion="Envíos de ejemplares entre sedes, con el historial de cada paso."
        acciones={
          tienePermiso(PERMISOS.REMITO_OPERAR) && <Button to="/remitos/nuevo">Nuevo remito</Button>
        }
      />
      <FilterBar etiqueta="Filtros de remitos" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <BusquedaConEspera
          etiqueta="Buscar por número"
          valor={filtros.numero ?? ''}
          onBuscar={(numero) => cambiar({ numero })}
        />
        <FiltroSelect
          etiqueta="Abiertos"
          valor={filtros.abiertos ?? ''}
          onCambiar={(abiertos) => cambiar({ abiertos })}
        >
          <option value="">Todos</option>
          <option value="si">Solo sin cerrar</option>
          <option value="atrasados">Sin despachar fuera de plazo</option>
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todos</option>
          {Object.entries(ESTADOS.remito).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Motivo"
          valor={filtros.motivo ?? ''}
          onCambiar={(motivo) => cambiar({ motivo })}
        >
          <option value="">Todos</option>
          {Object.entries(MOTIVOS_DE_REMITO).map(([valor, texto]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && <EmptyState titulo="No hay remitos que coincidan" />}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Remitos" columnas={columnas} filas={data.items} idDe={(r) => r.id} />
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
