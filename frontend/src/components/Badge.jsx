import estilos from './Badge.module.css';

/** Etiqueta de estado: siempre lleva texto; el color solo lo refuerza. */
export default function Badge({ tono = 'neutral', children }) {
  return <span className={`${estilos.badge} ${estilos[tono]}`}>{children}</span>;
}
