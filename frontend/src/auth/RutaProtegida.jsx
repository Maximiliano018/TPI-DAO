import { lazy, Suspense } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Alert, PageHeader, Spinner } from '../components/index.js';
import { useSesion } from './SesionContext.jsx';

// Se carga aparte: quien ya ingresó no descarga la página pública.
const InicioPublicoPage = lazy(() => import('../features/publico/pages/InicioPublicoPage.jsx'));

/**
 * Exige sesión y, opcionalmente, un rol o un permiso. La autorización real está en el backend:
 * esto solo evita mostrar pantallas que la persona no puede usar.
 *
 * @param {{roles?: string[], permiso?: string}} props
 */
export default function RutaProtegida({ roles, permiso, children }) {
  const { estado, usuario, aviso, tienePermiso } = useSesion();
  const ubicacion = useLocation();

  if (estado === 'cargando') return <Spinner texto="Restaurando la sesión…" />;
  // Sin sesión, la raíz muestra el inicio público; el resto de las pantallas pide ingresar. Si la
  // sesión se acaba de cerrar con un aviso (venció, sin conexión), se va al login para mostrarlo.
  if (estado !== 'autenticado' && ubicacion.pathname === '/' && !aviso) {
    return (
      <Suspense fallback={<Spinner />}>
        <InicioPublicoPage />
      </Suspense>
    );
  }
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
