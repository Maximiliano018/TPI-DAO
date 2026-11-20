import { useState } from 'react';
import { Alert, Button } from '../components/index.js';
import { accesoDemo } from '../utils/demo.js';
import { mensajeDeError } from '../utils/errores.js';
import { useSesion } from './SesionContext.jsx';
import estilos from './AccesoDemo.module.css';

/**
 * Cartel con el usuario y la contraseña de demostración y un botón que entra con un clic. Al
 * iniciar la sesión, la pantalla que lo contiene (inicio público o login) pasa sola al sistema.
 * No se muestra si el deploy no define el acceso (ver `utils/demo.js`).
 */
export default function AccesoDemo({ className = '' }) {
  const { iniciar } = useSesion();
  const [entrando, setEntrando] = useState(false);
  const [error, setError] = useState(null);
  const acceso = accesoDemo();
  if (!acceso) return null;

  async function entrar() {
    setError(null);
    setEntrando(true);
    try {
      await iniciar(acceso.usuario, acceso.clave);
    } catch (fallo) {
      setError(mensajeDeError(fallo));
      setEntrando(false);
    }
  }

  return (
    <section className={`${estilos.demo} ${className}`} aria-labelledby="titulo-demo">
      <h2 id="titulo-demo" className={estilos.titulo}>
        ¿Querés recorrer el sistema?
      </h2>
      <p className={estilos.texto}>
        Entrá con el usuario de demostración: podés ver todo, pero los cambios no se guardan.
      </p>
      <dl className={estilos.datos}>
        <div>
          <dt>Usuario</dt>
          <dd className="mono">{acceso.usuario}</dd>
        </div>
        <div>
          <dt>Contraseña</dt>
          <dd className="mono">{acceso.clave}</dd>
        </div>
      </dl>
      {error && <Alert tono="danger">{error}</Alert>}
      <Button variante="secondary" onClick={entrar} cargando={entrando}>
        Entrar como visitante <span aria-hidden="true">→</span>
      </Button>
    </section>
  );
}
