import { Badge } from '../../../components/index.js';
import { estadoDe } from '../../../utils/estados.js';

/** Estado de disponibilidad de un ejemplar. */
export default function EstadoEjemplarBadge({ estado }) {
  const { tono, texto } = estadoDe('ejemplar', estado);
  return <Badge tono={tono}>{texto}</Badge>;
}
