import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, ConfirmDialog, useToast } from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { useBajaUsuario, useReactivarUsuario } from '../hooks/useUsuarios.js';

/** Baja lógica: se conserva el historial y el administrador no puede darse de baja a sí mismo. */
export function BajaUsuarioDialog({ usuario, onCerrar }) {
  const baja = useBajaUsuario();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Dar de baja a ${usuario.nombre}`}
      descripcion="Dejará de poder ingresar. Se conserva su historial. Si es bibliotecario, deja de contar como asignado a su sede."
      textoConfirmar="Dar de baja"
      peligro
      procesando={baja.isPending}
      onConfirmar={() => {
        setFallo(null);
        baja.mutate(usuario.id, {
          onSuccess: () => {
            mostrar('Usuario dado de baja');
            onCerrar();
          },
          onError: setFallo,
        });
      }}
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** Reactivación: si su sede está en baja, hay que reasignarlo primero. */
export function ReactivarUsuarioDialog({ usuario, onCerrar }) {
  const reactivar = useReactivarUsuario();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Reactivar a ${usuario.nombre}`}
      descripcion="Volverá a poder ingresar con su usuario y contraseña."
      textoConfirmar="Reactivar"
      procesando={reactivar.isPending}
      onConfirmar={() => {
        setFallo(null);
        reactivar.mutate(usuario.id, {
          onSuccess: () => {
            mostrar('Usuario reactivado');
            onCerrar();
          },
          onError: setFallo,
        });
      }}
      onCancelar={onCerrar}
    >
      {fallo?.codigo === 'SEDE_EN_BAJA' ? (
        <Alert tono="warning">
          Su sede está dada de baja. Primero{' '}
          <Link to={`/usuarios/${usuario.id}/editar`}>asígnelo a una sede activa</Link> y luego
          reactívelo.
        </Alert>
      ) : (
        fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>
      )}
    </ConfirmDialog>
  );
}
