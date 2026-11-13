import { useState } from 'react';
import {
  Alert,
  ConfirmDialog,
  Input,
  Select,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_RECIBIDOS } from '../../../utils/estados.js';
import { formatearMonto } from '../../../utils/formato.js';
import { useRegistrarDevolucion } from '../hooks/useDevoluciones.js';

const CON_DESCRIPCION = ['DANADO', 'EXTRAVIADO'];

/** Resumen de lo que pasó con la devolución, para el aviso. */
export function resumenDeDevolucion(resultado) {
  const partes = [];
  if (resultado.multa) {
    const { monto_total: monto, dias_atraso: dias } = resultado.multa;
    partes.push(`multa de ${formatearMonto(monto)} por ${dias} día(s) de atraso`);
  }
  if (resultado.remito_retorno) {
    partes.push(`vuelve a su sede con el remito ${resultado.remito_retorno.numero}`);
  }
  if (resultado.reserva_asignada) {
    partes.push(`se asignó a la reserva ${resultado.reserva_asignada}`);
  }
  return partes.length ? `Devolución registrada: ${partes.join('; ')}` : 'Devolución registrada';
}

function efecto(prestamo, estado) {
  if (estado === 'EXTRAVIADO') return 'El ejemplar se da de baja y queda una incidencia del socio.';
  if (prestamo.tipo === 'INTERBIBLIOTECARIO') {
    return 'Se genera el remito de retorno a la sede propietaria del ejemplar.';
  }
  if (estado === 'DANADO') return 'El ejemplar pasa a revisión y queda una incidencia del socio.';
  return 'El ejemplar vuelve a estar disponible (o se asigna a la primera reserva del libro).';
}

/**
 * Registra la devolución de un préstamo activo o vencido en la sede destino.
 * Si pasó el vencimiento, el servidor genera la multa por los días de atraso.
 */
export default function DevolucionDialog({ prestamo, onCerrar }) {
  const registrar = useRegistrarDevolucion();
  const { mostrar } = useToast();
  const [estado, setEstado] = useState('BUENO');
  const [observaciones, setObservaciones] = useState('');
  const [fechaHora, setFechaHora] = useState('');
  const [fallo, setFallo] = useState(null);
  const exigeDescripcion = CON_DESCRIPCION.includes(estado);
  const faltaDescripcion = exigeDescripcion && !observaciones.trim();

  return (
    <ConfirmDialog
      titulo={`Devolución de ${prestamo.codigo_ejemplar}`}
      descripcion={`${prestamo.libro} · ${prestamo.socio}. ${efecto(prestamo, estado)}`}
      textoConfirmar="Registrar devolución"
      procesando={registrar.isPending}
      deshabilitarConfirmar={faltaDescripcion}
      onConfirmar={() => {
        setFallo(null);
        registrar.mutate(
          {
            id: prestamo.id,
            estado_fisico: estado,
            observaciones: observaciones.trim() || null,
            fecha_hora: fechaHora || null,
          },
          {
            onSuccess: (resultado) => {
              mostrar(resumenDeDevolucion(resultado));
              onCerrar();
            },
            onError: setFallo,
          },
        );
      }}
      onCancelar={onCerrar}
    >
      <Select
        etiqueta="Estado en que llega"
        value={estado}
        onChange={(e) => setEstado(e.target.value)}
      >
        {Object.entries(ESTADOS_RECIBIDOS).map(([valor, texto]) => (
          <option key={valor} value={valor}>
            {texto}
          </option>
        ))}
      </Select>
      <Textarea
        etiqueta="Observaciones"
        requerido={exigeDescripcion}
        ayuda={exigeDescripcion ? 'Describa el daño o el extravío.' : undefined}
        maxLength={300}
        rows={3}
        value={observaciones}
        onChange={(e) => setObservaciones(e.target.value)}
      />
      <Input
        etiqueta="Fecha y hora de la devolución (opcional)"
        ayuda="Solo si la devolvió antes y se registra ahora."
        type="datetime-local"
        value={fechaHora}
        onChange={(e) => setFechaHora(e.target.value)}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
