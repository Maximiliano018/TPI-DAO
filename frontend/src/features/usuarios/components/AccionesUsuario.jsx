import { useState } from 'react';
import { Button } from '../../../components/index.js';
import { BajaUsuarioDialog, ReactivarUsuarioDialog } from './UsuarioDialogs.jsx';

/** Editar y, según el estado, dar de baja o reactivar. Las acciones inválidas no aparecen. */
export default function AccionesUsuario({ usuario, tamano = 'sm' }) {
  const [dialogo, setDialogo] = useState(null);
  const cerrar = () => setDialogo(null);
  return (
    <>
      <Button
        to={`/usuarios/${usuario.id}/editar`}
        variante="secondary"
        tamano={tamano}
        aria-label={`Editar a ${usuario.nombre}`}
      >
        Editar
      </Button>
      {usuario.activo ? (
        <Button
          variante="danger"
          tamano={tamano}
          aria-label={`Dar de baja a ${usuario.nombre}`}
          onClick={() => setDialogo('baja')}
        >
          Dar de baja
        </Button>
      ) : (
        <Button
          variante="secondary"
          tamano={tamano}
          aria-label={`Reactivar a ${usuario.nombre}`}
          onClick={() => setDialogo('reactivar')}
        >
          Reactivar
        </Button>
      )}
      {dialogo === 'baja' && <BajaUsuarioDialog usuario={usuario} onCerrar={cerrar} />}
      {dialogo === 'reactivar' && <ReactivarUsuarioDialog usuario={usuario} onCerrar={cerrar} />}
    </>
  );
}
