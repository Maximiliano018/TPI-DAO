import { Badge } from '../../../components/index.js';
import { estadoDe } from '../../../utils/estados.js';

/** Estado de un préstamo o de un remito (`entidad` = `prestamo` o `remito`). */
export default function EstadoBadge({ entidad, estado }) {
  const { tono, texto } = estadoDe(entidad, estado);
  return <Badge tono={tono}>{texto}</Badge>;
}
