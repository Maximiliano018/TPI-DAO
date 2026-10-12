import { Badge, type VarianteBadge } from '../../components/Badge/Badge'
import { ESTADOS, type Entidad } from './estados'

type Props = {
  entidad: Entidad
  estado: string
}

/** Badge con el texto y el color del estado de una entidad del dominio. */
export function EstadoBadge({ entidad, estado }: Props) {
  const mapeo: Record<string, { texto: string; variante: VarianteBadge }> = ESTADOS[entidad]
  const datos = mapeo[estado] ?? { texto: estado, variante: 'neutral' }
  return <Badge variante={datos.variante}>{datos.texto}</Badge>
}
