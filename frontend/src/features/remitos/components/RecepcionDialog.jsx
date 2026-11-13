import { useState } from 'react';
import {
  Alert,
  Checkbox,
  ConfirmDialog,
  Input,
  Select,
  useToast,
} from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_FISICOS } from '../../../utils/estados.js';
import { useRecibirRemito } from '../../prestamos/hooks/usePrestamos.js';

/**
 * Recepción del remito en la sede destino: se verifica cada ejemplar. Un daño o una destrucción
 * exige describirlo (el backend lo vuelve a validar y registra la incidencia).
 */
export default function RecepcionDialog({ remito, onCerrar }) {
  const recibir = useRecibirRemito();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const [lineas, setLineas] = useState(() =>
    remito.lineas.map((l) => ({
      ejemplar_id: l.ejemplar_id,
      codigo: l.codigo_ejemplar,
      estado_fisico: l.estado_fisico_salida,
      destruido: false,
      observacion: '',
    })),
  );
  const cambiar = (i, cambios) =>
    setLineas((previas) => previas.map((l, j) => (j === i ? { ...l, ...cambios } : l)));

  return (
    <ConfirmDialog
      titulo={`Recibir ${remito.numero}`}
      descripcion="Verifique cada ejemplar. Si alguno llegó dañado o inutilizable, descríbalo."
      textoConfirmar="Confirmar recepción"
      procesando={recibir.isPending}
      onConfirmar={() => {
        setFallo(null);
        recibir.mutate(
          {
            id: remito.id,
            lineas: lineas.map(({ codigo: _codigo, observacion, ...resto }) => ({
              ...resto,
              observacion: observacion || null,
            })),
          },
          {
            onSuccess: () => {
              mostrar('Remito recibido');
              onCerrar();
            },
            onError: setFallo,
          },
        );
      }}
      onCancelar={onCerrar}
    >
      {lineas.map((linea, i) => (
        <fieldset key={linea.ejemplar_id} style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="mono">{linea.codigo}</legend>
          <Select
            etiqueta={`Estado físico de ${linea.codigo}`}
            value={linea.estado_fisico}
            onChange={(e) => cambiar(i, { estado_fisico: e.target.value })}
          >
            {Object.entries(ESTADOS_FISICOS).map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </Select>
          <Checkbox
            etiqueta="Llegó inutilizable (destruido)"
            checked={linea.destruido}
            onChange={(e) => cambiar(i, { destruido: e.target.checked })}
          />
          {(linea.destruido || linea.estado_fisico === 'DANADO') && (
            <Input
              etiqueta={`Qué le pasó a ${linea.codigo}`}
              requerido
              value={linea.observacion}
              onChange={(e) => cambiar(i, { observacion: e.target.value })}
            />
          )}
        </fieldset>
      ))}
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
