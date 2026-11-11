import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Button,
  Combobox,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroSelect,
  BusquedaConEspera,
  PageHeader,
  Pagination,
  Skeleton,
  Table,
} from '../../../components/index.js';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { PERMISOS, ROLES } from '../../../utils/roles.js';
import AbiertaBadge from '../components/AbiertaBadge.jsx';
import AccionesSede from '../components/AccionesSede.jsx';
import EstadoSedeBadge from '../components/EstadoSedeBadge.jsx';
import estilos from '../components/Sedes.module.css';
import { useLocalidades, useSedes } from '../hooks/useSedes.js';

/** Listado de sedes con filtros en la URL, orden, paginación y acciones por fila. */
export default function SedesPage() {
  useTituloDePagina('Sedes');
  const { usuario, tienePermiso } = useSesion();
  const administra = tienePermiso(PERMISOS.SEDE_ADMINISTRAR);
  const veEstado = usuario.rol !== ROLES.SOCIO;
  const estadoPorDefecto = administra ? 'TODAS' : 'ACTIVA';
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();

  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const orden = filtros.orden || 'nombre';
  const estado = filtros.estado || estadoPorDefecto;
  const localidadId = filtros.localidad_id ? Number(filtros.localidad_id) : '';

  const { data, isPending, error, refetch } = useSedes({
    estado: veEstado ? filtros.estado : undefined,
    q: filtros.q,
    localidad_id: localidadId,
    orden,
    page,
    size,
  });
  const localidades = useLocalidades();
  const opcionesLocalidad = (localidades.data ?? []).map((l) => ({
    id: l.id,
    texto: l.nombre,
    detalle: l.departamento,
  }));

  const columnas = [
    {
      clave: 'codigo',
      titulo: 'Código',
      orden: 'codigo',
      render: (s) => <span className={estilos.codigo}>{s.codigo}</span>,
    },
    {
      clave: 'nombre',
      titulo: 'Nombre',
      orden: 'nombre',
      render: (s) => <Link to={`/sedes/${s.id}`}>{s.nombre}</Link>,
    },
    { clave: 'localidad', titulo: 'Localidad', render: (s) => s.direccion.localidad },
    { clave: 'telefono', titulo: 'Teléfono', render: (s) => s.contacto.telefono },
    ...(veEstado
      ? [
          {
            clave: 'estado',
            titulo: 'Estado',
            render: (s) => <EstadoSedeBadge estado={s.estado} />,
          },
        ]
      : []),
    {
      clave: 'abierta',
      titulo: 'Abierta ahora',
      render: (s) => (s.estado === 'BAJA' ? '—' : <AbiertaBadge abierta={s.abierta_ahora} />),
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      render: (s) => (
        <div className={estilos.acciones}>
          <AccionesSede sede={s} conVer tamano="sm" />
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        titulo="Sedes"
        descripcion="Sedes de la red de bibliotecas."
        acciones={administra && <Button to="/sedes/nueva">Nueva sede</Button>}
      />
      <FilterBar etiqueta="Filtros de sedes" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        {veEstado && (
          <FiltroSelect
            etiqueta="Estado"
            valor={estado}
            onCambiar={(v) => cambiar({ estado: v === estadoPorDefecto ? '' : v })}
          >
            <option value="TODAS">Todas</option>
            <option value="ACTIVA">Activas</option>
            <option value="BAJA">En baja</option>
          </FiltroSelect>
        )}
        <BusquedaConEspera
          etiqueta="Buscar"
          valor={filtros.q ?? ''}
          onBuscar={(q) => cambiar({ q })}
        />
        <div className={estilos.filtroLocalidad}>
          <Combobox
            etiqueta="Localidad"
            opciones={opcionesLocalidad}
            valor={localidadId}
            onCambiar={(id) => cambiar({ localidad_id: id })}
            placeholder="Todas"
          />
        </div>
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState titulo="No hay sedes que coincidan">
          {hayFiltros && (
            <Button variante="secondary" onClick={limpiar}>
              Limpiar filtros
            </Button>
          )}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <>
          <Table
            etiqueta="Sedes"
            columnas={columnas}
            filas={data.items}
            idDe={(s) => s.id}
            orden={orden}
            onOrden={(o) => cambiar({ orden: o === 'nombre' ? '' : o })}
          />
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
