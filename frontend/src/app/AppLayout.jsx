import { Suspense, useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Spinner } from '../components/index.js';
import AppBar from './AppBar.jsx';
import Sidebar from './Sidebar.jsx';
import estilos from './AppLayout.module.css';

/** Estructura de toda pantalla autenticada: barra superior, menú lateral y `<main>`. */
export default function AppLayout() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const { pathname } = useLocation();

  // Al cambiar de pantalla se cierra el panel y se enfoca el título (lectores de pantalla).
  useEffect(() => {
    setMenuAbierto(false);
    document.querySelector('[data-page-title]')?.focus();
  }, [pathname]);

  return (
    <div className={estilos.estructura}>
      <a href="#contenido" className="skip-link">
        Saltar al contenido
      </a>
      <AppBar menuAbierto={menuAbierto} onAlternarMenu={() => setMenuAbierto((v) => !v)} />
      <Sidebar abierto={menuAbierto} onCerrar={() => setMenuAbierto(false)} />
      <main id="contenido" className={estilos.principal} tabIndex={-1}>
        <div className={estilos.contenido}>
          <Suspense fallback={<Spinner />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
