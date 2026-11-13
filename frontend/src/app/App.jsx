import { lazy } from 'react';
import { Outlet, Route, Routes } from 'react-router-dom';
import LoginPage from '../auth/LoginPage.jsx';
import RutaProtegida from '../auth/RutaProtegida.jsx';
import { PERMISOS } from '../utils/roles.js';
import VersionPage from '../features/sistema/pages/VersionPage.jsx';
import AppLayout from './AppLayout.jsx';
import NoEncontrada from './NoEncontrada.jsx';

const InicioPage = lazy(() => import('../features/inicio/pages/InicioPage.jsx'));
const SedesPage = lazy(() => import('../features/sedes/pages/SedesPage.jsx'));
const SedeDetallePage = lazy(() => import('../features/sedes/pages/SedeDetallePage.jsx'));
const SedeFormPage = lazy(() => import('../features/sedes/pages/SedeFormPage.jsx'));
const UsuariosPage = lazy(() => import('../features/usuarios/pages/UsuariosPage.jsx'));
const UsuarioFormPage = lazy(() => import('../features/usuarios/pages/UsuarioFormPage.jsx'));
const SociosPage = lazy(() => import('../features/socios/pages/SociosPage.jsx'));
const SocioDetallePage = lazy(() => import('../features/socios/pages/SocioDetallePage.jsx'));
const SocioFormPage = lazy(() => import('../features/socios/pages/SocioFormPage.jsx'));
const MisDatosPage = lazy(() => import('../features/socios/pages/MisDatosPage.jsx'));
const CatalogoPage = lazy(() => import('../features/catalogo/pages/CatalogoPage.jsx'));
const LibroDetallePage = lazy(() => import('../features/catalogo/pages/LibroDetallePage.jsx'));
const LibroFormPage = lazy(() => import('../features/catalogo/pages/LibroFormPage.jsx'));
const EjemplaresPage = lazy(() => import('../features/catalogo/pages/EjemplaresPage.jsx'));
const EjemplarDetallePage = lazy(
  () => import('../features/catalogo/pages/EjemplarDetallePage.jsx'),
);
const EjemplarFormPage = lazy(() => import('../features/catalogo/pages/EjemplarFormPage.jsx'));

/** Rutas de la aplicación. Cada módulo suma las suyas con `React.lazy`. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/version" element={<VersionPage />} />
      <Route
        element={
          <RutaProtegida>
            <AppLayout />
          </RutaProtegida>
        }
      >
        <Route index element={<InicioPage />} />
        <Route path="sedes" element={<SedesPage />} />
        <Route
          path="sedes/nueva"
          element={
            <RutaProtegida permiso={PERMISOS.SEDE_ADMINISTRAR}>
              <SedeFormPage modo="crear" />
            </RutaProtegida>
          }
        />
        <Route path="sedes/:id" element={<SedeDetallePage />} />
        <Route
          path="sedes/:id/editar"
          element={
            <RutaProtegida permiso={PERMISOS.SEDE_ADMINISTRAR}>
              <SedeFormPage modo="editar" />
            </RutaProtegida>
          }
        />
        <Route
          path="usuarios"
          element={
            <RutaProtegida permiso={PERMISOS.USUARIO_ADMINISTRAR}>
              <Outlet />
            </RutaProtegida>
          }
        >
          <Route index element={<UsuariosPage />} />
          <Route path="nuevo" element={<UsuarioFormPage modo="crear" />} />
          <Route path=":id/editar" element={<UsuarioFormPage modo="editar" />} />
        </Route>
        <Route
          path="socios"
          element={
            <RutaProtegida permiso={PERMISOS.SOCIO_LEER}>
              <Outlet />
            </RutaProtegida>
          }
        >
          <Route index element={<SociosPage />} />
          <Route path=":id" element={<SocioDetallePage />} />
          <Route
            path="nuevo"
            element={
              <RutaProtegida permiso={PERMISOS.SOCIO_REGISTRAR}>
                <SocioFormPage modo="crear" />
              </RutaProtegida>
            }
          />
          <Route
            path=":id/editar"
            element={
              <RutaProtegida permiso={PERMISOS.SOCIO_REGISTRAR}>
                <SocioFormPage modo="editar" />
              </RutaProtegida>
            }
          />
        </Route>
        <Route
          path="mis-datos"
          element={
            <RutaProtegida permiso={PERMISOS.SOCIO_VER_PROPIO}>
              <MisDatosPage />
            </RutaProtegida>
          }
        />
        <Route
          path="catalogo"
          element={
            <RutaProtegida permiso={PERMISOS.CATALOGO_LEER}>
              <Outlet />
            </RutaProtegida>
          }
        >
          <Route index element={<CatalogoPage />} />
          <Route path=":id" element={<LibroDetallePage />} />
          <Route
            path="nuevo"
            element={
              <RutaProtegida permiso={PERMISOS.CATALOGO_ADMINISTRAR}>
                <LibroFormPage modo="crear" />
              </RutaProtegida>
            }
          />
          <Route
            path=":id/editar"
            element={
              <RutaProtegida permiso={PERMISOS.CATALOGO_ADMINISTRAR}>
                <LibroFormPage modo="editar" />
              </RutaProtegida>
            }
          />
        </Route>
        <Route
          path="ejemplares"
          element={
            <RutaProtegida permiso={PERMISOS.EJEMPLAR_LEER}>
              <Outlet />
            </RutaProtegida>
          }
        >
          <Route index element={<EjemplaresPage />} />
          <Route
            path="nuevo"
            element={
              <RutaProtegida permiso={PERMISOS.EJEMPLAR_ADMINISTRAR}>
                <EjemplarFormPage />
              </RutaProtegida>
            }
          />
          <Route path=":id" element={<EjemplarDetallePage />} />
        </Route>
        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  );
}
