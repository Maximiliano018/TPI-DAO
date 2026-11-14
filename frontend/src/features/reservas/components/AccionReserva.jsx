import { useState } from 'react';
import { Alert, ConfirmDialog, Input, useToast } from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { useCancelarReserva, useRetirarReserva } from '../hooks/useReservas.js';

/** Confirmación para entregar (`retirar`) o cancelar una reserva; la cancelación pide motivo. */
export default function AccionReserva({ reserva, tipo, onCerrar }) {
  const cancelar = useCancelarReserva();
  const retirar = useRetirarReserva();
  const entrega = tipo === 'retirar';
  const mutacion = entrega ? retirar : cancelar;
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const [motivo, setMotivo] = useState('');
  return (
    <ConfirmDialog
      titulo={`${entrega ? 'Entregar' : 'Cancelar'} la reserva ${reserva.numero}`}
      descripcion={
        entrega
          ? `Se entrega ${reserva.codigo_ejemplar} y empieza el préstamo.`
          : 'Si ya tenía un ejemplar asignado, pasa al siguiente de la cola.'
      }
      textoConfirmar={entrega ? 'Entregar' : 'Cancelar reserva'}
      peligro={!entrega}
      procesando={mutacion.isPending}
      onConfirmar={() => {
        setFallo(null);
        mutacion.mutate(entrega ? reserva.id : { id: reserva.id, motivo: motivo.trim() || null }, {
          onSuccess: () => {
            mostrar(entrega ? 'Reserva entregada' : 'Reserva cancelada');
            onCerrar();
          },
          onError: setFallo,
        });
      }}
      onCancelar={onCerrar}
    >
      {!entrega && (
        <Input
          etiqueta="Motivo (opcional)"
          value={motivo}
          maxLength={300}
          onChange={(e) => setMotivo(e.target.value)}
        />
      )}
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
