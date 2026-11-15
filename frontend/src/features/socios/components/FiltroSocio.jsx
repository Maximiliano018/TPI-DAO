import { Card, Skeleton } from '../../../components/index.js';
import estilos from './FiltroSocio.module.css';
import { useSocio } from '../hooks/useSocios.js';
import ElegirSocio from './ElegirSocio.jsx';

/** Filtro por socio para el personal (multas y reportes): busca y elige un socio. */
export default function FiltroSocio({ socioId, onCambiar }) {
  const socio = useSocio(socioId, { enabled: Boolean(socioId) });
  if (socioId && socio.isPending) return <Skeleton alto={32} />;
  return (
    <div className={estilos.filtro}>
      <Card titulo="Socio">
        <ElegirSocio
          elegido={socioId ? socio.data : null}
          onElegir={(elegido) => onCambiar(elegido ? elegido.id : '')}
        />
      </Card>
    </div>
  );
}
