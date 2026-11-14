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
import { TIPOS_DE_MATERIAL } from '../../../utils/estados.js';
import { PERMISOS } from '../../../utils/roles.js';
import { useCategorias, useLibros } from '../hooks/useCatalogo.js';

/** Búsqueda en el catálogo común de la red, con los ejemplares disponibles de cada libro. */
export default function CatalogoPage() {
  useTituloDePagina('Catálogo');
  const { tienePermiso } = useSesion();
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const categorias = useCategorias();
  const { data, isPending, error, refetch } = useLibros({
    q: filtros.q,
    categoria_id: filtros.categoria_id,
    tipo_material: filtros.tipo_material,
    page,
    size,
  });

  const columnas = [
    {
      clave: 'titulo',
      titulo: 'Título',
      render: (lb) => <Link to={`/catalogo/${lb.id}`}>{lb.titulo}</Link>,
    },
    { clave: 'autores', titulo: 'Autores', render: (lb) => lb.autores.join(', ') },
    { clave: 'categoria', titulo: 'Categoría', render: (lb) => lb.categoria.nombre },
    {
      clave: 'disponibles',
      titulo: 'Disponibles',
      render: (lb) =>
        lb.disponibles > 0 ? (
          <Badge tono="success">{`${lb.disponibles} de ${lb.ejemplares}`}</Badge>
        ) : (
          <Badge tono="neutral">{lb.ejemplares ? 'Sin disponibles' : 'Sin ejemplares'}</Badge>
        ),
    },
  ];

  return (
    <>
      <PageHeader
        titulo="Catálogo"
        descripcion="Libros de toda la red. Un libro disponible en otra sede se puede pedir como préstamo interbibliotecario."
        acciones={
          tienePermiso(PERMISOS.CATALOGO_ADMINISTRAR) && (
            <Button to="/catalogo/nuevo">Nuevo libro</Button>
          )
        }
      />
      <FilterBar etiqueta="Filtros del catálogo" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <BusquedaConEspera
          etiqueta="Buscar por título, autor o ISBN"
          valor={filtros.q ?? ''}
          onBuscar={(q) => cambiar({ q })}
        />
        <FiltroSelect
          etiqueta="Categoría"
          valor={filtros.categoria_id ?? ''}
          onCambiar={(categoriaId) => cambiar({ categoria_id: categoriaId })}
        >
          <option value="">Todas</option>
          {(categorias.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Tipo de material"
          valor={filtros.tipo_material ?? ''}
          onCambiar={(tipo) => cambiar({ tipo_material: tipo })}
        >
          <option value="">Todos</option>
          {Object.entries(TIPOS_DE_MATERIAL).map(([valor, texto]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState titulo="No hay libros que coincidan">
          {hayFiltros && (
            <Button variante="secondary" onClick={limpiar}>
              Limpiar filtros
            </Button>
          )}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Libros" columnas={columnas} filas={data.items} idDe={(lb) => lb.id} />
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
