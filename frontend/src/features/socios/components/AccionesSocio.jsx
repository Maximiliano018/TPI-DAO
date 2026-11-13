import { useState } from 'react';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { Button } from '../../../components/index.js';
import { PERMISOS } from '../../../utils/roles.js';
import {
  BajaSocioDialog,
  CrearCuentaDialog,
  InhabilitarSocioDialog,
  ReactivarSocioDialog,
  RehabilitarSocioDialog,
} from './SocioDialogs.jsx';

/**
 * Acciones de la ficha según el estado del socio y el rol. Las que no aplican no se muestran;
 * el backend vuelve a validar cada una.
 */
export default function AccionesSocio({ socio }) {
  const { tienePermiso } = useSesion();
  const [dialogo, setDialogo] = useState(null);
  const cerrar = () => setDialogo(null);
  const registra = tienePermiso(PERMISOS.SOCIO_REGISTRAR);
  const administra = tienePermiso(PERMISOS.SOCIO_ADMINISTRAR);
  const enBaja = socio.estado === 'BAJA';
  const administrativa = socio.motivo_inhabilitacion === 'ADMINISTRATIVA';
  const puedeRehabilitar =
    socio.estado === 'INHABILITADO' && (administra || (registra && !administrativa));

  const boton = (clave, texto, variante = 'secondary') => (
    <Button variante={variante} onClick={() => setDialogo(clave)}>
      {texto}
    </Button>
  );

  return (
    <>
      {registra && !enBaja && (
        <Button to={`/socios/${socio.id}/editar`} variante="secondary">
          Editar
        </Button>
      )}
      {registra && !enBaja && !socio.cuenta && boton('cuenta', 'Crear cuenta')}
      {puedeRehabilitar && boton('rehabilitar', 'Rehabilitar')}
      {administra && !enBaja && !administrativa && boton('inhabilitar', 'Inhabilitar', 'danger')}
      {administra && !enBaja && boton('baja', 'Dar de baja', 'danger')}
      {administra && enBaja && boton('reactivar', 'Reactivar')}

      {dialogo === 'cuenta' && <CrearCuentaDialog socio={socio} onCerrar={cerrar} />}
      {dialogo === 'rehabilitar' && <RehabilitarSocioDialog socio={socio} onCerrar={cerrar} />}
      {dialogo === 'inhabilitar' && <InhabilitarSocioDialog socio={socio} onCerrar={cerrar} />}
      {dialogo === 'baja' && <BajaSocioDialog socio={socio} onCerrar={cerrar} />}
      {dialogo === 'reactivar' && <ReactivarSocioDialog socio={socio} onCerrar={cerrar} />}
    </>
  );
}
