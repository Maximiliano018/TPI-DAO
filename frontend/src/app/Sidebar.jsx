import { useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useSesion } from '../auth/SesionContext.jsx';
import { useAtraparFoco } from '../hooks/useAtraparFoco.js';
import { ITEMS_DE_MENU } from './navegacion.js';
import estilos from './Sidebar.module.css';

/** Menú lateral: fijo desde 1024 px; por debajo es un panel que atrapa el foco y cierra con Escape. */
export default function Sidebar({ abierto, onCerrar }) {
  const { tienePermiso } = useSesion();
  const ref = useRef(null);
  useAtraparFoco(ref, abierto, onCerrar);
  const items = ITEMS_DE_MENU.filter((item) => !item.permiso || tienePermiso(item.permiso));

  return (
    <>
      {abierto && <div className={estilos.velo} onClick={onCerrar} aria-hidden="true" />}
      <nav
        id="menu-lateral"
        ref={ref}
        aria-label="Navegación principal"
        className={`${estilos.menu} ${abierto ? estilos.abierto : ''}`}
      >
        <ul>
          {items.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.fin}
                className={({ isActive }) => `${estilos.enlace} ${isActive ? estilos.activo : ''}`}
                onClick={onCerrar}
              >
                {item.texto}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
