import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroSelect,
  Skeleton,
} from '../../../components/index.js';
import estilosFiltro from '../../../components/FilterBar.module.css';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { descargarCsv } from '../../../utils/csv.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import estilos from './Reportes.module.css';

/** Consulta de un reporte; no se emite mientras el rango de fechas sea inválido. */
export function useReporte(nombre, consulta, params, { habilitado = true } = {}) {
  const limpios = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== ''),
  );
  return useQuery({
    queryKey: ['reportes', nombre, limpios],
    queryFn: () => consulta(limpios),
    placeholderData: keepPreviousData,
    enabled: habilitado,
  });
}

/**
 * Filtros de un reporte guardados en la URL. «Limpiar» borra los del reporte y conserva la
 * pestaña elegida (`r`).
 */
export function useFiltrosDeReporte(claves) {
  const { filtros, cambiar } = useFiltrosUrl();
  const hayFiltros = claves.some((clave) => filtros[clave]);
  const limpiar = () => cambiar(Object.fromEntries(claves.map((clave) => [clave, ''])));
  const rangoInvalido = Boolean(filtros.desde && filtros.hasta && filtros.hasta < filtros.desde);
  return { filtros, cambiar, limpiar, hayFiltros, rangoInvalido };
}

export function FiltroFecha({ etiqueta, valor, onCambiar }) {
  return (
    <label className={estilosFiltro.campo}>
      <span className={estilosFiltro.etiqueta}>{etiqueta}</span>
      <input
        type="date"
        className={estilosFiltro.control}
        value={valor ?? ''}
        onChange={(e) => onCambiar(e.target.value)}
      />
    </label>
  );
}

/** Sede del reporte: el administrador elige; el bibliotecario ve siempre la suya. */
export function FiltroSede({ valor, onCambiar, paraTodos = false }) {
  const { usuario } = useSesion();
  const elige = paraTodos || usuario.rol === 'ADMIN';
  const sedes = useSedes({ estado: 'TODAS', orden: 'nombre', size: 100 }, { enabled: elige });
  if (!elige) return null;
  return (
    <FiltroSelect etiqueta="Sede" valor={valor ?? ''} onCambiar={onCambiar}>
      <option value="">Toda la red</option>
      {sedes.data?.items.map((s) => (
        <option key={s.id} value={s.id}>
          {s.nombre}
        </option>
      ))}
    </FiltroSelect>
  );
}

/** Barra de filtros con período (desde y hasta) más los propios del reporte. */
export function FiltrosConPeriodo({ etiqueta, control, conPeriodo = true, children }) {
  const { filtros, cambiar, limpiar, hayFiltros, rangoInvalido } = control;
  return (
    <>
      <FilterBar etiqueta={etiqueta} onLimpiar={limpiar} hayFiltros={hayFiltros}>
        {conPeriodo && (
          <>
            <FiltroFecha
              etiqueta="Desde"
              valor={filtros.desde}
              onCambiar={(desde) => cambiar({ desde })}
            />
            <FiltroFecha
              etiqueta="Hasta"
              valor={filtros.hasta}
              onCambiar={(hasta) => cambiar({ hasta })}
            />
          </>
        )}
        {children}
      </FilterBar>
      {rangoInvalido && (
        <Alert tono="danger">La fecha «Hasta» no puede ser anterior a «Desde».</Alert>
      )}
    </>
  );
}

/** Carga, error y «sin resultados» comunes; `vacio` decide si hay algo para mostrar. */
export function Resultado({ consulta, vacio, children }) {
  const { data, isPending, error, refetch, fetchStatus } = consulta;
  if (isPending && fetchStatus === 'idle') return null;
  if (isPending) return <Skeleton alto={160} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  if (vacio(data)) {
    return (
      <EmptyState
        titulo="Sin resultados"
        descripcion="No hay datos registrados para estos filtros."
      />
    );
  }
  return children(data);
}

/** Indicadores del reporte (tarjetas con un número). */
export function Indicadores({ items }) {
  return (
    <div className={estilos.indicadores}>
      {items.map(({ etiqueta, valor }) => (
        <section key={etiqueta} className={estilos.indicador} aria-label={etiqueta}>
          <h2 className={estilos.etiqueta}>{etiqueta}</h2>
          <p className={estilos.valor}>{valor}</p>
        </section>
      ))}
    </div>
  );
}

/** Exporta a CSV las mismas filas que muestra la tabla (RF-REP-10). */
export function BotonCsv({ nombre, columnas, filas }) {
  return (
    <Button
      variante="secondary"
      tamano="sm"
      onClick={() => descargarCsv(nombre, columnas, filas)}
      disabled={filas.length === 0}
    >
      Exportar CSV
    </Button>
  );
}

/** Título de una sección del reporte con su botón de exportación. */
export function Seccion({ titulo, acciones, children }) {
  return (
    <section className={estilos.seccion} aria-label={titulo}>
      <div className={estilos.encabezado}>
        <h2 className={estilos.titulo}>{titulo}</h2>
        {acciones}
      </div>
      {children}
    </section>
  );
}
