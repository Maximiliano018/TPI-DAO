import { Badge } from '../../../components/index.js';
import { MOTIVOS_DE_INHABILITACION, estadoDe } from '../../../utils/estados.js';
import estilos from './EstadoSocioBadge.module.css';

/**
 * Estado del socio; si está inhabilitado muestra la causa debajo del cartel («Préstamo vencido»)
 * para que todos los carteles tengan el mismo ancho. `enLinea` la pone al costado (encabezados).
 */
export default function EstadoSocioBadge({ socio, enLinea = false }) {
  const { tono, texto } = estadoDe('socio', socio.estado);
  const motivo = MOTIVOS_DE_INHABILITACION[socio.motivo_inhabilitacion];
  if (!motivo) return <Badge tono={tono}>{texto}</Badge>;
  return (
    <span className={`${estilos.estado} ${enLinea ? estilos.enLinea : ''}`}>
      <Badge tono={tono}>{texto}</Badge>
      <span className={estilos.motivo}>{motivo}</span>
    </span>
  );
}
