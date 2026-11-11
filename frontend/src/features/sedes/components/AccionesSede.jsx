import { useState } from 'react';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { Button } from '../../../components/index.js';
import { PERMISOS } from '../../../utils/roles.js';
import { BajaDialog, ReactivarDialog } from './BajaDialogs.jsx';

/**
 * Acciones de una sede según el rol y el estado: las que no corresponden no se muestran.
 * `conVer` agrega el enlace al detalle (listado); el detalle ya está en esa pantalla.
 */
export default function AccionesSede({ sede, conVer = false, tamano = 'md' }) {
  const { tienePermiso } = useSesion();
  const [dialogo, setDialogo] = useState(null);
  const administra = tienePermiso(PERMISOS.SEDE_ADMINISTRAR);
  const enBaja = sede.estado === 'BAJA';
  const cerrar = () => setDialogo(null);

  return (
    <>
      {conVer && (
        <Button
          to={`/sedes/${sede.id}`}
          variante="secondary"
          tamano={tamano}
          aria-label={`Ver ${sede.nombre}`}
        >
          Ver
        </Button>
      )}
      {administra && !enBaja && (
        <>
          <Button
            to={`/sedes/${sede.id}/editar`}
            variante="secondary"
            tamano={tamano}
            aria-label={`Editar ${sede.nombre}`}
          >
            Editar
          </Button>
          <Button
            variante="danger"
            tamano={tamano}
            aria-label={`Dar de baja ${sede.nombre}`}
            onClick={() => setDialogo('baja')}
          >
            Dar de baja
          </Button>
        </>
      )}
      {administra && enBaja && (
        <Button
          variante="secondary"
          tamano={tamano}
          aria-label={`Reactivar ${sede.nombre}`}
          onClick={() => setDialogo('reactivar')}
        >
          Reactivar
        </Button>
      )}
      {dialogo === 'baja' && <BajaDialog sede={sede} onCerrar={cerrar} />}
      {dialogo === 'reactivar' && <ReactivarDialog sede={sede} onCerrar={cerrar} />}
    </>
  );
}
