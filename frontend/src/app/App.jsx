import { lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import LoginPage from '../auth/LoginPage.jsx';
import RutaProtegida from '../auth/RutaProtegida.jsx';
import VersionPage from '../features/sistema/pages/VersionPage.jsx';
import AppLayout from './AppLayout.jsx';
import NoEncontrada from './NoEncontrada.jsx';

const InicioPage = lazy(() => import('../features/inicio/pages/InicioPage.jsx'));

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
        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  );
}
