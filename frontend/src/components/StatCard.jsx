import { Link } from 'react-router-dom';
import ErrorState from './ErrorState.jsx';
import { Skeleton } from './Spinner.jsx';
import estilos from './StatCard.module.css';

/** Indicador del inicio con estados de carga y error propios. */
export default function StatCard({ etiqueta, valor, to, cargando, error, onReintentar }) {
  return (
    <section className={estilos.tarjeta} aria-label={etiqueta}>
      <h2 className={estilos.etiqueta}>{etiqueta}</h2>
      {cargando && <Skeleton alto={36} ancho="4ch" />}
      {error && <ErrorState error={error} onReintentar={onReintentar} />}
      {!cargando && !error && <p className={estilos.valor}>{valor}</p>}
      {to && !error && (
        <Link to={to} className={estilos.enlace}>
          Ver detalle
        </Link>
      )}
    </section>
  );
}
