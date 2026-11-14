import { useState } from 'react';
import {
  EmptyState,
  ErrorState,
  Pagination,
  Skeleton,
  Timeline,
} from '../../../components/index.js';
import { MOTIVOS_DE_INHABILITACION, TIPOS_DE_BAJA, estadoDe } from '../../../utils/estados.js';
import { formatearFechaHora } from '../../../utils/formato.js';
import { useHistorialSocio } from '../hooks/useSocios.js';

export const EVENTOS = {
  ALTA: 'Alta del socio',
  MODIFICACION: 'Modificación de datos',
  INHABILITACION: 'Inhabilitación administrativa',
  REHABILITACION: 'Rehabilitación',
  CAMBIO_AUTOMATICO: 'Cambio automático de estado',
  BAJA: 'Baja',
  SOLICITUD_REACTIVACION: 'Solicitud de reactivación',
  SOLICITUD_RECHAZADA: 'Solicitud de reactivación rechazada',
  REACTIVACION: 'Reactivación',
  CUENTA_CREADA: 'Cuenta de acceso creada',
};

const CAMPOS = {
  tipo_documento: 'Tipo de documento',
  nro_documento: 'Documento',
  nombre: 'Nombre',
  apellido: 'Apellido',
  fecha_nacimiento: 'Fecha de nacimiento',
  email: 'Correo',
  telefono: 'Teléfono',
  domicilio: 'Domicilio',
  causas: 'Causas',
  tipo_baja: 'Tipo de baja',
  cuenta: 'Usuario',
};

/** Valor de un cambio en texto legible. */
function texto(campo, valor) {
  if (valor === null || valor === undefined || valor === '') return '—';
  if (campo === 'causas') {
    return valor.length
      ? valor.map((c) => MOTIVOS_DE_INHABILITACION[c] ?? c).join(', ')
      : 'ninguna';
  }
  if (campo === 'tipo_baja') return TIPOS_DE_BAJA[valor] ?? valor;
  return typeof valor === 'string' ? valor : JSON.stringify(valor);
}

function Contenido({ evento }) {
  const hayEstado = evento.estado_nuevo && evento.estado_anterior !== evento.estado_nuevo;
  return (
    <>
      {hayEstado && (
        <p style={{ margin: 0 }}>
          Estado: {evento.estado_anterior ? estadoDe('socio', evento.estado_anterior).texto : '—'} →{' '}
          {estadoDe('socio', evento.estado_nuevo).texto}
        </p>
      )}
      {evento.origen && <p style={{ margin: 0 }}>Origen: {evento.origen}</p>}
      {evento.motivo && <p style={{ margin: 0 }}>Motivo: {evento.motivo}</p>}
      {evento.cambios.length > 0 && evento.tipo_evento !== 'ALTA' && (
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {evento.cambios.map((c, i) => (
            <li key={`${c.campo}-${i}`}>
              {CAMPOS[c.campo] ?? c.campo}: {texto(c.campo, c.antes)} → {texto(c.campo, c.despues)}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/**
 * Historial del socio, del más reciente al más antiguo. El personal ve quién hizo cada cambio;
 * el socio ve «Vos», «Personal de la biblioteca» o «Sistema» (lo resuelve el servidor).
 */
export default function HistorialSocio({ socioId }) {
  const [page, setPage] = useState(1);
  const { data, isPending, error, refetch } = useHistorialSocio(socioId, { page, size: 10 });

  if (isPending) return <Skeleton alto={120} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  if (data.items.length === 0) return <EmptyState titulo="Sin eventos para mostrar" />;
  return (
    <>
      <Timeline
        etiqueta="Historial del socio"
        items={data.items.map((e) => ({
          id: e.id,
          titulo: EVENTOS[e.tipo_evento] ?? e.tipo_evento,
          meta: `${e.autor} · ${formatearFechaHora(e.fecha_hora)}`,
          contenido: <Contenido evento={e} />,
        }))}
      />
      <Pagination page={data.page} size={data.size} total={data.total} onPage={setPage} />
    </>
  );
}
