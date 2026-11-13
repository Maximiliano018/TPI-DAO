import { useSesion } from '../../../auth/SesionContext.jsx';
import SocioDetallePage from './SocioDetallePage.jsx';

/** «Mis datos» del socio: su propia ficha, tomada de la sesión. */
export default function MisDatosPage() {
  const { usuario } = useSesion();
  return <SocioDetallePage socioId={usuario.socio_id} />;
}
