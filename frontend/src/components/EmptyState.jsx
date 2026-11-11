import estilos from './EmptyState.module.css';

/** Estado vacío: qué pasa y cuál es la acción siguiente. */
export default function EmptyState({ titulo, descripcion, children }) {
  return (
    <div className={estilos.vacio}>
      <p className={estilos.titulo}>{titulo}</p>
      {descripcion && <p className={estilos.descripcion}>{descripcion}</p>}
      {children}
    </div>
  );
}
