import estilos from './Timeline.module.css';

/**
 * Línea de tiempo vertical.
 *
 * @param {{items: {id: string|number, titulo: import('react').ReactNode, meta?: import('react').ReactNode, contenido?: import('react').ReactNode}[]}} props
 */
export default function Timeline({ items, etiqueta }) {
  return (
    <ol className={estilos.linea} aria-label={etiqueta}>
      {items.map((item) => (
        <li key={item.id} className={estilos.item}>
          <div className={estilos.cabecera}>
            <strong>{item.titulo}</strong>
            {item.meta && <span className={estilos.meta}>{item.meta}</span>}
          </div>
          {item.contenido}
        </li>
      ))}
    </ol>
  );
}
