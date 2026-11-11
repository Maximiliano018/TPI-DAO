import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSesion } from '../auth/SesionContext.jsx';
import { Button } from '../components/index.js';
import { MENSAJES } from '../utils/mensajes.js';
import { NOMBRE_DE_ROL } from '../utils/roles.js';
import estilos from './AppBar.module.css';

/** Barra superior: menú (pantallas chicas), nombre del sistema, sede y menú de usuario. */
export default function AppBar({ menuAbierto, onAlternarMenu }) {
  const { usuario, cerrar } = useSesion();
  const navegar = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;
    const fuera = (e) => !contenedor.current?.contains(e.target) && setAbierto(false);
    const escape = (e) => e.key === 'Escape' && setAbierto(false);
    document.addEventListener('mousedown', fuera);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', fuera);
      document.removeEventListener('keydown', escape);
    };
  }, [abierto]);

  function salir() {
    cerrar();
    navegar('/login', { replace: true });
  }

  return (
    <header className={estilos.barra}>
      <button
        type="button"
        className={estilos.menu}
        aria-label="Menú de navegación"
        aria-expanded={menuAbierto}
        aria-controls="menu-lateral"
        onClick={onAlternarMenu}
      >
        ☰
      </button>
      <span className={estilos.sistema}>{MENSAJES.sistema}</span>
      <span className={estilos.sede} data-testid="sede-del-usuario">
        {usuario.sede ? usuario.sede.nombre : MENSAJES.todaLaRed}
      </span>
      <div className={estilos.usuario} ref={contenedor}>
        <button
          type="button"
          className={estilos.boton}
          aria-haspopup="true"
          aria-expanded={abierto}
          onClick={() => setAbierto((v) => !v)}
        >
          {usuario.nombre} <span aria-hidden="true">▾</span>
        </button>
        {abierto && (
          <div className={estilos.panel} role="group" aria-label="Menú de usuario">
            <p className={estilos.datos}>
              <strong>{usuario.nombre}</strong>
              <span>{NOMBRE_DE_ROL[usuario.rol] ?? usuario.rol}</span>
            </p>
            <Button variante="secondary" tamano="sm" onClick={salir}>
              Cerrar sesión
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
