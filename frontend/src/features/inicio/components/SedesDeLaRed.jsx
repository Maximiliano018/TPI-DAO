import { Link } from 'react-router-dom';
import { Card, EmptyState, ErrorState, Skeleton } from '../../../components/index.js';
import { diaSemanaISO, textoHorarioDelDia } from '../../../utils/formato.js';
import AbiertaBadge from '../../sedes/components/AbiertaBadge.jsx';
import EstadoSedeBadge from '../../sedes/components/EstadoSedeBadge.jsx';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import estilos from './Inicio.module.css';

/**
 * Lista de sedes de la red con «abierta ahora» y el horario de hoy.
 *
 * @param {{titulo: string, filtros?: object, excluirId?: number, mostrarEstado?: boolean}} props
 */
export default function SedesDeLaRed({ titulo, filtros = {}, excluirId, mostrarEstado = false }) {
  const { data, isPending, error, refetch } = useSedes({ size: 20, ...filtros });
  const sedes = (data?.items ?? []).filter((sede) => sede.id !== excluirId);
  const hoy = diaSemanaISO();

  return (
    <Card titulo={titulo}>
      {isPending && <Skeleton alto={64} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && sedes.length === 0 && <EmptyState titulo="No hay sedes para mostrar" />}
      {sedes.length > 0 && (
        <ul className={estilos.lista}>
          {sedes.map((sede) => (
            <li key={sede.id} className={estilos.elemento}>
              <div>
                <Link to={`/sedes/${sede.id}`}>{sede.nombre}</Link>{' '}
                <span className="mono">{sede.codigo}</span>
                <p className={estilos.detalle}>
                  Hoy: {textoHorarioDelDia(sede.horarios, hoy)} · {sede.contacto.telefono}
                </p>
              </div>
              <div className={estilos.estados}>
                {mostrarEstado && sede.estado && <EstadoSedeBadge estado={sede.estado} />}
                {sede.estado !== 'BAJA' && <AbiertaBadge abierta={sede.abierta_ahora} />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
