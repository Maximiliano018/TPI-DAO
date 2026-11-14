import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  ErrorState,
  PageHeader,
  Skeleton,
  Timeline,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { estadoDe } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import AccionReserva from '../components/AccionReserva.jsx';
import { useReserva } from '../hooks/useReservas.js';
import { puedeCancelar, puedeEntregar } from '../permisos.js';

function Acciones({ reserva }) {
  const { usuario, tienePermiso } = useSesion();
  const [tipo, setTipo] = useState(null);
  return (
    <>
      {puedeEntregar(reserva, usuario, tienePermiso) && (
        <Button onClick={() => setTipo('retirar')}>Entregar</Button>
      )}
      {puedeCancelar(reserva, usuario, tienePermiso) && (
        <Button variante="danger" onClick={() => setTipo('cancelar')}>
          Cancelar reserva
        </Button>
      )}
      {tipo && <AccionReserva reserva={reserva} tipo={tipo} onCerrar={() => setTipo(null)} />}
    </>
  );
}

/** Ficha de la reserva: situación en la cola, retiro y el historial de cada cambio de estado. */
export default function ReservaDetallePage() {
  const { id } = useParams();
  const { tienePermiso } = useSesion();
  const { data: reserva, isPending, error, refetch } = useReserva(id);
  useTituloDePagina(reserva?.numero ?? 'Reserva');
  const esPersonal = tienePermiso(PERMISOS.RESERVA_LEER);
  const migas = [
    { texto: esPersonal ? 'Reservas' : 'Mis reservas', to: '/reservas' },
    { texto: reserva?.numero ?? 'Reserva' },
  ];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Reserva" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        titulo={reserva.numero}
        descripcion={
          <>
            {reserva.libro} <EstadoBadge entidad="reserva" estado={reserva.estado} />
          </>
        }
        migas={<Breadcrumb items={migas} />}
        acciones={<Acciones reserva={reserva} />}
      />
      <div className={inicio.pagina}>
        {reserva.estado === 'PENDIENTE' && (
          <Alert tono="info">
            Lugar {reserva.posicion_en_cola} en la cola. Cuando se libere un ejemplar se asigna al
            primero de la cola.
          </Alert>
        )}
        {reserva.estado === 'DISPONIBLE_PARA_RETIRO' && (
          <Alert tono="success">
            {esPersonal ? 'El socio puede retirar' : 'Podés retirar'}{' '}
            <span className="mono">{reserva.codigo_ejemplar}</span> en {reserva.sede_retiro} hasta
            el {formatearFecha(reserva.vencimiento_retiro)}.
          </Alert>
        )}
        <div className={estilos.datos}>
          <Card titulo="Reserva">
            <dl className={estilos.definiciones}>
              <dt>Libro</dt>
              <dd>
                <Link to={`/catalogo/${reserva.libro_id}`}>{reserva.libro}</Link>
              </dd>
              <dt>Socio</dt>
              <dd>
                {esPersonal ? (
                  <Link to={`/socios/${reserva.socio_id}`}>{reserva.socio}</Link>
                ) : (
                  reserva.socio
                )}{' '}
                <span className="mono">{reserva.numero_socio}</span>
              </dd>
              <dt>Retira en</dt>
              <dd>{reserva.sede_retiro}</dd>
              <dt>Reservada</dt>
              <dd>{formatearFechaHora(reserva.fecha_reserva)}</dd>
              {esPersonal && (
                <>
                  <dt>Registrada por</dt>
                  <dd>{reserva.registrada_por?.nombre ?? 'Sin dato'}</dd>
                </>
              )}
              {reserva.codigo_ejemplar && (
                <>
                  <dt>Ejemplar</dt>
                  <dd className="mono">{reserva.codigo_ejemplar}</dd>
                </>
              )}
              {reserva.prestamo_id && (
                <>
                  <dt>Préstamo</dt>
                  <dd>
                    <Link to={`/prestamos/${reserva.prestamo_id}`}>Ver préstamo</Link>
                  </dd>
                </>
              )}
              {reserva.fecha_cierre && (
                <>
                  <dt>Cerrada</dt>
                  <dd>{formatearFechaHora(reserva.fecha_cierre)}</dd>
                </>
              )}
            </dl>
          </Card>
          <Card titulo="Historial">
            <Timeline
              etiqueta="Historial de la reserva"
              items={[...reserva.historial].reverse().map((m, i) => ({
                id: i,
                titulo: estadoDe('reserva', m.estado_nuevo).texto,
                // El socio ve «Vos», «Personal de la biblioteca» o «Sistema» (lo resuelve la API).
                meta: `${m.autor} · ${formatearFechaHora(m.fecha_hora)}`,
                contenido: m.observacion && <p style={{ margin: 0 }}>{m.observacion}</p>,
              }))}
            />
          </Card>
        </div>
      </div>
    </>
  );
}
