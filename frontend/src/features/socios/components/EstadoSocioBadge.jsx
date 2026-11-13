import { Badge } from '../../../components/index.js';
import { MOTIVOS_DE_INHABILITACION, estadoDe } from '../../../utils/estados.js';

/** Estado del socio; si está inhabilitado agrega la causa («Inhabilitado · Préstamo vencido»). */
export default function EstadoSocioBadge({ socio }) {
  const { tono, texto } = estadoDe('socio', socio.estado);
  const motivo = MOTIVOS_DE_INHABILITACION[socio.motivo_inhabilitacion];
  return <Badge tono={tono}>{motivo ? `${texto} · ${motivo}` : texto}</Badge>;
}
