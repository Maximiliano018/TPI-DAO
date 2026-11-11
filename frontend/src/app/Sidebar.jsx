import { useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useSesion } from '../auth/SesionContext.jsx';
import { useAtraparFoco } from '../hooks/useAtraparFoco.js';
import { ITEMS_DE_MENU } from './navegacion.js';
import estilos from './Sidebar.module.css';

// Estantes decorativos bajo la pila: libros de pie (color, alto, ancho, inclinación en grados).
const ESTANTES = [
  [
    ['bosque', 64, 18],
    ['burdeos', 74, 14],
    ['ocre', 58, 20],
    ['marino', 70, 16, -8],
    ['ciruela', 66, 15],
  ],
  [
    ['petroleo', 70, 17],
    ['burdeos', 60, 22],
    ['marino', 76, 13],
    ['ocre', 64, 18],
    ['bosque', 72, 15, 7],
  ],
  [
    ['ciruela', 68, 16],
    ['ocre', 76, 14],
    ['petroleo', 58, 21],
    ['burdeos', 72, 15],
    ['marino', 62, 18],
  ],
  [
    ['bosque', 74, 15],
    ['marino', 62, 20],
    ['burdeos', 70, 14, -6],
    ['ocre', 66, 17],
    ['petroleo', 76, 14],
  ],
];

/**
 * Menú lateral con forma de estantería: cada ítem es un libro apilado sobre una tabla de madera.
 * El libro de la página actual sobresale y lleva un marcador (no depende solo del color).
 * Fijo desde 1024 px; por debajo es un panel que atrapa el foco y cierra con Escape.
 */
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
        <ul className={estilos.pila}>
          {items.map((item) => (
            <li key={item.to} className={estilos.libro}>
              <NavLink
                to={item.to}
                end={item.fin}
                className={({ isActive }) => `${estilos.lomo} ${isActive ? estilos.activo : ''}`}
                onClick={onCerrar}
              >
                <span className={estilos.titulo}>{item.texto}</span>
                <span className={estilos.paginas} aria-hidden="true" />
              </NavLink>
            </li>
          ))}
        </ul>
        <div className={estilos.tabla} aria-hidden="true" />
        <div className={estilos.estantes} aria-hidden="true">
          {ESTANTES.map((libros, fila) => (
            <div key={fila} className={estilos.estante}>
              <div className={estilos.fila}>
                {libros.map(([color, alto, ancho, giro = 0], i) => (
                  <span
                    key={i}
                    className={estilos.parado}
                    style={{
                      '--c': `var(--lomo-${color})`,
                      height: alto,
                      width: ancho,
                      transform: giro ? `rotate(${giro}deg)` : undefined,
                    }}
                  />
                ))}
              </div>
              <div className={estilos.tabla} />
            </div>
          ))}
        </div>
      </nav>
    </>
  );
}
