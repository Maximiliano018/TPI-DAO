import { useId, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useSesion } from '../auth/SesionContext.jsx';
import { Icono } from '../components/index.js';
import { useAtraparFoco } from '../hooks/useAtraparFoco.js';
import { SECCIONES_DE_MENU } from './navegacion.js';
import estilos from './Sidebar.module.css';

/** Una sección del menú: su nombre y sus opciones, todas con la franja del color de la sección. */
function Seccion({ titulo, franja, items, onCerrar }) {
  const id = useId();
  return (
    <div className={estilos.seccion} style={{ '--franja': `var(--lomo-${franja})` }}>
      {titulo && (
        <span id={id} className={estilos.cartela}>
          {titulo}
        </span>
      )}
      <ul className={estilos.pila} aria-labelledby={titulo ? id : undefined}>
        {items.map((item) => (
          <li key={item.texto}>
            <NavLink
              to={item.to}
              end={item.fin}
              className={({ isActive }) => `${estilos.enlace} ${isActive ? estilos.activo : ''}`}
              onClick={onCerrar}
            >
              <Icono nombre={item.icono} />
              {item.texto}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Menú lateral de nogal: cada sección con su nombre en latón y cada opción con su ícono y la
 * franja de color de la sección. La opción actual es una hoja crema con un marcador de cinta (no
 * depende solo del color). Fijo desde 1024 px; por debajo es un panel que atrapa el foco y cierra
 * con Escape.
 */
export default function Sidebar({ abierto, onCerrar }) {
  const { tienePermiso } = useSesion();
  const ref = useRef(null);
  useAtraparFoco(ref, abierto, onCerrar);
  const secciones = SECCIONES_DE_MENU.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => !item.permiso || tienePermiso(item.permiso)),
  })).filter((seccion) => seccion.items.length > 0);

  return (
    <>
      {abierto && <div className={estilos.velo} onClick={onCerrar} aria-hidden="true" />}
      <nav
        id="menu-lateral"
        ref={ref}
        aria-label="Navegación principal"
        className={`${estilos.menu} ${abierto ? estilos.abierto : ''}`}
      >
        {secciones.map((seccion) => (
          <Seccion
            key={seccion.titulo ?? 'inicio'}
            titulo={seccion.titulo}
            franja={seccion.franja}
            items={seccion.items}
            onCerrar={onCerrar}
          />
        ))}
      </nav>
    </>
  );
}
