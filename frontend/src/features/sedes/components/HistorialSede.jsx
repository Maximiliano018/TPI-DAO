import { useState } from 'react';
import {
  Alert,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroFecha,
  FiltroSelect,
  Pagination,
  Skeleton,
  Timeline,
} from '../../../components/index.js';
import { estadoDe } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { useHistorialSede } from '../hooks/useSedes.js';
import estilos from './Sedes.module.css';

export const EVENTOS = {
  ALTA: 'Alta de la sede',
  MODIFICACION: 'Modificación',
  BAJA: 'Baja',
  REACTIVACION: 'Reactivación',
  EXCEPCION_AGREGADA: 'Cierre agregado',
  EXCEPCION_ELIMINADA: 'Cierre quitado',
};

const CAMPOS = {
  excepcion: 'Cierre',
  nombre: 'Nombre',
  calle: 'Calle',
  numero: 'Número',
  localidad: 'Localidad',
  telefono: 'Teléfono',
  email: 'Correo',
  responsable: 'Responsable',
  horarios: 'Horarios',
};

const TIPOS_DE_CIERRE = { CIERRE_TOTAL: 'cierre total', CIERRE_PARCIAL: 'cierre parcial' };

const esCierre = (valor) =>
  valor && typeof valor === 'object' && 'fecha' in valor && 'tipo' in valor;

/** Valor de un cambio en texto: los cierres se describen; el resto se muestra tal cual. */
const texto = (valor) => {
  if (valor === null || valor === undefined || valor === '') return '—';
  if (esCierre(valor)) {
    const horas = valor.hora_desde ? ` de ${valor.hora_desde} a ${valor.hora_hasta}` : '';
    const motivo = valor.motivo ? ` (${valor.motivo})` : '';
    return `${formatearFecha(valor.fecha)}, ${TIPOS_DE_CIERRE[valor.tipo] ?? valor.tipo}${horas}${motivo}`;
  }
  return typeof valor === 'string' ? valor : JSON.stringify(valor);
};

function Contenido({ evento }) {
  const hayEstado = evento.estado_anterior || evento.estado_nuevo;
  return (
    <>
      {hayEstado && (
        <p style={{ margin: 0 }}>
          Estado: {evento.estado_anterior ? estadoDe('sede', evento.estado_anterior).texto : '—'} →{' '}
          {estadoDe('sede', evento.estado_nuevo).texto}
        </p>
      )}
      {evento.motivo && <p style={{ margin: 0 }}>Motivo: {evento.motivo}</p>}
      {evento.cambios.length > 0 && (
        <ul className={estilos.cambios}>
          {evento.cambios.map((c, i) => (
            <li key={`${c.campo}-${i}`}>
              {CAMPOS[c.campo] ?? c.campo}: {texto(c.antes)} → {texto(c.despues)}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Línea de tiempo de auditoría (solo administrador), paginada y con filtro por tipo y fechas. */
export default function HistorialSede({ sedeId }) {
  const [tipo, setTipo] = useState('');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [page, setPage] = useState(1);
  const rangoInvalido = Boolean(desde && hasta && hasta < desde);
  const { data, isPending, error, refetch } = useHistorialSede(
    sedeId,
    { tipo_evento: tipo, desde, hasta, page, size: 10 },
    { enabled: !rangoInvalido },
  );
  const filtrar = (cambiar) => (valor) => {
    cambiar(valor);
    setPage(1);
  };

  return (
    <div className={estilos.seccion}>
      <FilterBar
        etiqueta="Filtros del historial"
        hayFiltros={Boolean(tipo || desde || hasta)}
        onLimpiar={() => {
          setTipo('');
          setDesde('');
          setHasta('');
          setPage(1);
        }}
      >
        <FiltroSelect etiqueta="Tipo de evento" valor={tipo} onCambiar={filtrar(setTipo)}>
          <option value="">Todos</option>
          {Object.entries(EVENTOS).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </FiltroSelect>
        <FiltroFecha etiqueta="Desde" valor={desde} onCambiar={filtrar(setDesde)} />
        <FiltroFecha etiqueta="Hasta" valor={hasta} onCambiar={filtrar(setHasta)} />
      </FilterBar>
      {rangoInvalido ? (
        <Alert tono="danger">La fecha «Hasta» no puede ser anterior a «Desde».</Alert>
      ) : (
        isPending && <Skeleton alto={120} />
      )}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && <EmptyState titulo="Sin eventos para mostrar" />}
      {data && data.items.length > 0 && (
        <>
          <Timeline
            etiqueta="Historial de la sede"
            items={data.items.map((e) => ({
              id: e.id,
              titulo: EVENTOS[e.tipo_evento] ?? e.tipo_evento,
              meta: `${e.usuario.nombre} · ${formatearFechaHora(e.fecha_hora)}`,
              contenido: <Contenido evento={e} />,
            }))}
          />
          <Pagination page={data.page} size={data.size} total={data.total} onPage={setPage} />
        </>
      )}
    </div>
  );
}
