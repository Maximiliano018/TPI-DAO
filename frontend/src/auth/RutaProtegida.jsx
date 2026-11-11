import { Navigate, useLocation } from 'react-router-dom';
import { Alert, PageHeader, Spinner } from '../components/index.js';
import { useSesion } from './SesionContext.jsx';

/**
 * Exige sesión y, opcionalmente, un rol o un permiso. La autorización real está en el backend:
 * esto solo evita mostrar pantallas que la persona no puede usar.
 *
 * @param {{roles?: string[], permiso?: string}} props
 */
export default function RutaProtegida({ roles, permiso, children }) {
  const { estado, usuario, tienePermiso } = useSesion();
  const ubicacion = useLocation();

  if (estado === 'cargando') return <Spinner texto="Restaurando la sesión…" />;
  if (estado !== 'autenticado') {
    return (
      <Navigate to="/login" replace state={{ desde: ubicacion.pathname + ubicacion.search }} />
    );
  }
  const rolPermitido = !roles || roles.includes(usuario.rol);
  const permisoPermitido = !permiso || tienePermiso(permiso);
  if (!rolPermitido || !permisoPermitido) {
    return (
      <>
        <PageHeader titulo="Sin permiso" />
        <Alert tono="warning">No tiene permiso para ver esta pantalla.</Alert>
      </>
    );
  }
  return children;
}
