import { Link } from 'react-router-dom';
import estilos from './Button.module.css';

/**
 * Botón del design system. Con `to` se muestra como enlace de navegación con el mismo aspecto.
 *
 * @param {{variante?: 'primary'|'secondary'|'danger'|'link', tamano?: 'md'|'sm', cargando?: boolean, to?: string}} props
 */
export default function Button({
  variante = 'primary',
  tamano = 'md',
  cargando = false,
  to,
  type = 'button',
  disabled = false,
  className = '',
  children,
  ...resto
}) {
  const clases = [estilos.boton, estilos[variante], estilos[tamano], className]
    .filter(Boolean)
    .join(' ');
  if (to) {
    return (
      <Link to={to} className={clases} {...resto}>
        {children}
      </Link>
    );
  }
  return (
    <button
      type={type}
      className={clases}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...resto}
    >
      {cargando && <span className={estilos.spinner} aria-hidden="true" />}
      {children}
    </button>
  );
}
