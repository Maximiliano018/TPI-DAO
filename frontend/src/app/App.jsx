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
        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  );
}
