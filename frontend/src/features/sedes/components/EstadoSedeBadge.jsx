import { Badge } from '../../../components/index.js';
import { estadoDe } from '../../../utils/estados.js';

export default function EstadoSedeBadge({ estado }) {
  const { tono, texto } = estadoDe('sede', estado);
  return <Badge tono={tono}>{texto}</Badge>;
}
