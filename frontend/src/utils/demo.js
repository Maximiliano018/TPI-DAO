/**
 * Acceso de demostración para quien visita el proyecto publicado. Solo existe si el deploy define
 * `VITE_DEMO_USUARIO` y `VITE_DEMO_CLAVE`; sin esas variables no se muestra nada. Ese usuario
 * tiene que figurar en `USUARIOS_SOLO_LECTURA` del backend, que le rechaza cualquier cambio.
 *
 * @returns {{usuario: string, clave: string} | null}
 */
export function accesoDemo() {
  const usuario = import.meta.env.VITE_DEMO_USUARIO?.trim();
  const clave = import.meta.env.VITE_DEMO_CLAVE;
  return usuario && clave ? { usuario, clave } : null;
}
