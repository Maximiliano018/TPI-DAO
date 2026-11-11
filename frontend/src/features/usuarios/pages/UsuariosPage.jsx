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
import { estadoDe } from '../../../utils/estados.js';
import { MENSAJES } from '../../../utils/mensajes.js';
import { NOMBRE_DE_ROL } from '../../../utils/roles.js';
import { Badge } from '../../../components/index.js';
import estilos from '../../sedes/components/Sedes.module.css';
import AccionesUsuario from '../components/AccionesUsuario.jsx';
import { useSedesParaElegir, useUsuarios } from '../hooks/useUsuarios.js';

const ACTIVO_DE = { activos: true, baja: false };

/** Listado del personal (administradores y bibliotecarios) con filtros en la URL. */
export default function UsuariosPage() {
  useTituloDePagina('Usuarios');
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;

  const { data, isPending, error, refetch } = useUsuarios({
    rol: filtros.rol,
    sede_id: filtros.sede_id,
    activo: ACTIVO_DE[filtros.estado],
    q: filtros.q,
    page,
    size,
  });
  const sedes = useSedesParaElegir({ soloActivas: false });

  const columnas = [
    {
      clave: 'username',
      titulo: 'Usuario',
      render: (u) => <span className={estilos.codigo}>{u.username}</span>,
    },
    { clave: 'nombre', titulo: 'Nombre' },
    { clave: 'rol', titulo: 'Rol', render: (u) => NOMBRE_DE_ROL[u.rol] ?? u.rol },
    { clave: 'sede', titulo: 'Sede', render: (u) => u.sede?.nombre ?? MENSAJES.todaLaRed },
    {
      clave: 'estado',
      titulo: 'Estado',
      render: (u) => {
        const { tono, texto } = estadoDe('usuario', u.activo ? 'ACTIVO' : 'BAJA');
        return <Badge tono={tono}>{texto}</Badge>;
      },
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      render: (u) => (
        <div className={estilos.acciones}>
          <AccionesUsuario usuario={u} />
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        titulo="Usuarios"
        descripcion="Administradores y bibliotecarios del sistema."
        acciones={<Button to="/usuarios/nuevo">Nuevo usuario</Button>}
      />
      <FilterBar etiqueta="Filtros de usuarios" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <FiltroSelect
          etiqueta="Rol"
          valor={filtros.rol ?? ''}
          onCambiar={(rol) => cambiar({ rol })}
        >
          <option value="">Todos</option>
          <option value="ADMIN">{NOMBRE_DE_ROL.ADMIN}</option>
          <option value="BIBLIOTECARIO">{NOMBRE_DE_ROL.BIBLIOTECARIO}</option>
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Sede"
          valor={filtros.sede_id ?? ''}
          onCambiar={(sedeId) => cambiar({ sede_id: sedeId })}
        >
          <option value="">Todas</option>
          {(sedes.data?.items ?? []).map((sede) => (
            <option key={sede.id} value={sede.id}>
              {sede.nombre}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todos</option>
          <option value="activos">Activos</option>
          <option value="baja">Dados de baja</option>
        </FiltroSelect>
        <BusquedaConEspera
          etiqueta="Buscar por nombre o usuario"
          valor={filtros.q ?? ''}
          onBuscar={(q) => cambiar({ q })}
        />
      </FilterBar>

      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState titulo="No hay usuarios que coincidan">
          {hayFiltros && (
            <Button variante="secondary" onClick={limpiar}>
              Limpiar filtros
            </Button>
          )}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Usuarios" columnas={columnas} filas={data.items} idDe={(u) => u.id} />
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
