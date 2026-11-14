import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  ConfirmDialog,
  Select,
  Skeleton,
  useToast,
} from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { formatearFecha } from '../../../utils/formato.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import { usePropuestaPrestamo, useSolicitarPrestamo } from '../hooks/usePrestamos.js';

function Propuesta({ propuesta }) {
  if (propuesta.tipo === 'LOCAL') {
    return (
      <Alert tono="success">
        Hay un ejemplar disponible en {propuesta.sede_destino.nombre}. Queda apartado para vos:
        retiralo en el mostrador hasta el {formatearFecha(propuesta.retiro_hasta)}. Tenés{' '}
        {propuesta.plazo_dias} días para devolverlo desde que lo retirás.
      </Alert>
    );
  }
  return (
    <Alert tono="info">
      Préstamo entre sedes: el ejemplar sale de {propuesta.sede_origen.nombre} y lo retirás en{' '}
      {propuesta.sede_destino.nombre}. Cuando llegue, en «Mis préstamos» vas a ver hasta qué día
      podés retirarlo. Tenés {propuesta.plazo_dias} días para devolverlo desde que lo retirás.
    </Alert>
  );
}

/**
 * Autogestión: el socio pide un libro para sí. Elige dónde retirarlo (por defecto, su sede de
 * alta) y el sistema propone el tipo de préstamo y la sede de donde sale el ejemplar. Si no hay
 * disponibles en la red, ofrece reservar.
 */
export default function SolicitarPrestamoDialog({ libro, onCerrar, onReservar }) {
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 });
  const [sedeId, setSedeId] = useState('');
  const propuesta = usePropuestaPrestamo({
    libro_id: libro.id,
    ...(sedeId ? { sede_destino_id: sedeId } : {}),
  });
  const solicitar = useSolicitarPrestamo();
  const [fallo, setFallo] = useState(null);
  const [cambio, setCambio] = useState(false);

  const error = propuesta.error;
  const sinDisponibles = error?.codigo === 'SIN_EJEMPLARES_DISPONIBLES';
  const destino =
    sedeId ||
    String(propuesta.data?.sede_destino.id ?? error?.detalles?.[0]?.sede_destino_id ?? '');

  function confirmar() {
    setFallo(null);
    setCambio(false);
    solicitar.mutate(
      {
        libro_id: libro.id,
        sede_destino_id: propuesta.data.sede_destino.id,
        sede_origen_esperada_id: propuesta.data.sede_origen.id,
      },
      {
        onSuccess: (prestamo) => {
          mostrar(`Préstamo ${prestamo.numero} solicitado`);
          navegar(`/prestamos/${prestamo.id}`);
        },
        onError: (e) => {
          if (e.codigo === 'DISPONIBILIDAD_CAMBIADA') {
            setCambio(true);
            propuesta.refetch();
          } else {
            setFallo(e);
          }
        },
      },
    );
  }

  return (
    <ConfirmDialog
      titulo={`Pedir «${libro.titulo}»`}
      descripcion="El sistema elige el ejemplar: de tu sede si hay, o de otra sede si no."
      textoConfirmar="Pedir préstamo"
      procesando={solicitar.isPending}
      deshabilitarConfirmar={!propuesta.data || propuesta.isFetching}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <Select
        etiqueta="Lo retiro en"
        requerido
        value={destino}
        onChange={(e) => {
          setSedeId(e.target.value);
          setCambio(false);
        }}
      >
        {destino === '' && <option value="">Elegí la sede</option>}
        {(sedes.data?.items ?? []).map((s) => (
          <option key={s.id} value={s.id}>
            {s.nombre}
          </option>
        ))}
      </Select>
      {propuesta.isFetching && <Skeleton alto={48} />}
      {cambio && (
        <Alert tono="warning">
          La disponibilidad cambió mientras confirmabas. Revisá la nueva propuesta.
        </Alert>
      )}
      {!propuesta.isFetching && propuesta.data && <Propuesta propuesta={propuesta.data} />}
      {!propuesta.isFetching && sinDisponibles && (
        <Alert tono="info">
          {mensajeDeError(error)}{' '}
          {onReservar && (
            <Button tamano="sm" variante="secondary" onClick={onReservar}>
              Reservar
            </Button>
          )}
        </Alert>
      )}
      {!propuesta.isFetching && error && !sinDisponibles && (
        <Alert tono="danger">{mensajeDeError(error)}</Alert>
      )}
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
