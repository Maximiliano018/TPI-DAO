import estilos from './Spinner.module.css';

/** Indicador de carga con texto accesible. */
export function Spinner({ texto = 'Cargando…' }) {
  return (
    <div className={estilos.contenedor} role="status">
      <span className={estilos.rueda} aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}

/** Bloque de esqueleto para reservar espacio mientras llegan los datos. */
export function Skeleton({ alto = 20, ancho = '100%' }) {
  return (
    <div className={estilos.esqueleto} style={{ height: alto, width: ancho }} aria-hidden="true" />
  );
}
