import { Badge } from '../../../components/index.js';

/** Indicador «abierta ahora»: siempre con texto, el color solo lo refuerza. */
export default function AbiertaBadge({ abierta }) {
  return abierta ? <Badge tono="success">Abierta</Badge> : <Badge tono="neutral">Cerrada</Badge>;
}
