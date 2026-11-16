import { Link } from 'react-router-dom';
import Icono from './Icono.jsx';
import estilos from './Button.module.css';

/**
 * Botón del design system. Con `to` se muestra como enlace de navegación con el mismo aspecto.
 * `icono` agrega un dibujo antes del texto (ver `Icono.jsx`); el nombre accesible sigue siendo
 * el texto. Con `soloIcono` el texto queda oculto a la vista (lo leen los lectores de pantalla)
 * y aparece como ayuda al pasar el mouse: sirve para las acciones de cada fila de una tabla.
 *
 * @param {{variante?: 'primary'|'secondary'|'danger'|'link', tamano?: 'md'|'sm', cargando?: boolean, to?: string, icono?: string, soloIcono?: boolean}} props
 */
export default function Button({
  variante = 'primary',
  tamano = 'md',
  cargando = false,
  to,
  type = 'button',
  disabled = false,
  className = '',
  icono,
  soloIcono = false,
  children,
  ...resto
}) {
  const conIcono = soloIcono && icono;
  const clases = [
    estilos.boton,
    estilos[variante],
    estilos[tamano],
    conIcono && estilos.soloIcono,
    className,
  ]
    .filter(Boolean)
    .join(' ');
  const texto = conIcono ? <span className="sr-only">{children}</span> : children;
  const ayuda = conIcono ? (resto['aria-label'] ?? children) : undefined;
  if (to) {
    return (
      <Link to={to} className={clases} title={ayuda} {...resto}>
        {icono && <Icono nombre={icono} />}
        {texto}
      </Link>
    );
  }
  return (
    <button
      type={type}
      className={clases}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      title={ayuda}
      {...resto}
    >
      {cargando && <span className={estilos.spinner} aria-hidden="true" />}
      {!cargando && icono && <Icono nombre={icono} />}
      {texto}
    </button>
  );
}
