import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Alert,
  Button,
  ConfirmDialog,
  Modal,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { useBajaSede, useReactivarSede } from '../hooks/useSedesMutaciones.js';
import ConflictoVersionDialog from './ConflictoVersionDialog.jsx';

const MIN_MOTIVO = 5;
const MAX_MOTIVO = 300;

const TITULOS_IMPEDIMENTO = {
  PRESTAMOS_EN_CURSO: 'Préstamos en curso',
  REMITOS_ABIERTOS: 'Remitos abiertos',
  RESERVAS_PENDIENTES: 'Reservas pendientes',
  EJEMPLARES_EN_SEDE: 'Ejemplares alojados en la sede',
  EJEMPLARES_PROPIOS_FUERA: 'Ejemplares propios fuera de la sede',
  BIBLIOTECARIOS_ASIGNADOS: 'Bibliotecarios asignados',
};

/** Lista por tipo de lo que impide la baja, sin ofrecer forzarla. */
function BajaBloqueadaDialog({ sede, error, onCerrar }) {
  return (
    <Modal
      titulo="No se puede dar de baja la sede"
      onCerrar={onCerrar}
      acciones={
        <Button onClick={onCerrar} data-autofocus>
          Entendido
        </Button>
      }
    >
      <p style={{ marginTop: 0 }}>{error.mensaje}</p>
      <ul>
        {error.detalles.map((impedimento) => (
          <li key={impedimento.tipo}>
            <strong>
              {TITULOS_IMPEDIMENTO[impedimento.tipo] ?? impedimento.tipo} ({impedimento.cantidad})
            </strong>
            {impedimento.elementos.length > 0 && (
              <>
                {': '}
                {impedimento.elementos.map((e) => e.referencia).join(', ')}
                {impedimento.hay_mas &&
                  ` y ${impedimento.cantidad - impedimento.elementos.length} más`}
              </>
            )}
            {impedimento.tipo === 'BIBLIOTECARIOS_ASIGNADOS' && (
              <>
                {' · '}
                <Link to={`/usuarios?sede_id=${sede.id}&estado=activos`}>
                  Ver bibliotecarios de la sede
                </Link>
              </>
            )}
          </li>
        ))}
      </ul>
    </Modal>
  );
}

/** Baja con motivo obligatorio (5 a 300 caracteres). */
export function BajaDialog({ sede, onCerrar }) {
  const [motivo, setMotivo] = useState('');
  const [fallo, setFallo] = useState(null);
  const baja = useBajaSede(sede.id);
  const { mostrar } = useToast();
  const largo = motivo.trim().length;

  if (fallo?.codigo === 'SEDE_CON_ACTIVIDAD_PENDIENTE')
    return <BajaBloqueadaDialog sede={sede} error={fallo} onCerrar={onCerrar} />;
  if (fallo?.codigo === 'CONFLICTO_DE_VERSION')
    return <ConflictoVersionDialog onRecargar={onCerrar} />;

  function confirmar() {
    setFallo(null);
    baja.mutate(
      { motivo: motivo.trim(), version: sede.version },
      {
        onSuccess: () => {
          mostrar('Sede dada de baja', 'success');
          onCerrar();
        },
        onError: setFallo,
      },
    );
  }

  return (
    <ConfirmDialog
      titulo={`Dar de baja ${sede.nombre}`}
      descripcion="La sede dejará de operar. No se cancelan préstamos ni envíos: la baja se bloquea si hay actividad pendiente."
      textoConfirmar="Dar de baja"
      peligro
      procesando={baja.isPending}
      deshabilitarConfirmar={largo < MIN_MOTIVO || largo > MAX_MOTIVO}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
      <Textarea
        etiqueta="Motivo de la baja"
        requerido
        rows={3}
        data-autofocus
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        ayuda={`${largo}/${MAX_MOTIVO} caracteres (mínimo ${MIN_MOTIVO})`}
      />
    </ConfirmDialog>
  );
}

/** Reactivación: no pide datos. */
export function ReactivarDialog({ sede, onCerrar }) {
  const [fallo, setFallo] = useState(null);
  const reactivar = useReactivarSede(sede.id);
  const { mostrar } = useToast();

  if (fallo?.codigo === 'CONFLICTO_DE_VERSION')
    return <ConflictoVersionDialog onRecargar={onCerrar} />;

  return (
    <ConfirmDialog
      titulo={`Reactivar ${sede.nombre}`}
      descripcion="La sede volverá a operar. Se conserva su historial."
      textoConfirmar="Reactivar"
      procesando={reactivar.isPending}
      onConfirmar={() => {
        setFallo(null);
        reactivar.mutate(
          { version: sede.version },
          {
            onSuccess: () => {
              mostrar('Sede reactivada', 'success');
              onCerrar();
            },
            onError: setFallo,
          },
        );
      }}
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
