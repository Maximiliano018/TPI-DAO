import { Link } from 'react-router-dom';
import estilos from './Breadcrumb.module.css';

/** Migas de pan; el último elemento es la página actual. */
export default function Breadcrumb({ items }) {
  return (
    <nav aria-label="Migas de pan" className={estilos.migas}>
      <ol>
        {items.map((item, indice) => {
          const ultimo = indice === items.length - 1;
          return (
            <li key={item.texto}>
              {ultimo || !item.to ? (
                <span aria-current={ultimo ? 'page' : undefined}>{item.texto}</span>
              ) : (
                <Link to={item.to}>{item.texto}</Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
