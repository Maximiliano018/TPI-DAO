import { Link } from 'react-router-dom';
import { Card, ErrorState, Skeleton } from '../../../components/index.js';
import { diaSemanaISO, formatearFecha, textoHorarioDelDia } from '../../../utils/formato.js';
import AbiertaBadge from '../../sedes/components/AbiertaBadge.jsx';
import { useSede } from '../../sedes/hooks/useSedes.js';
import SedesDeLaRed from './SedesDeLaRed.jsx';
import estilos from './Inicio.module.css';

function MiSede({ sedeId }) {
  const { data: sede, isPending, error, refetch } = useSede(sedeId);
  return (
    <Card titulo="Mi sede">
      {isPending && <Skeleton alto={96} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {sede && (
        <div className={estilos.miSede}>
          <p className={estilos.nombre}>
            <Link to={`/sedes/${sede.id}`}>{sede.nombre}</Link>{' '}
            <span className="mono">{sede.codigo}</span>{' '}
            <AbiertaBadge abierta={sede.abierta_ahora} />
          </p>
          <p>
            {sede.direccion.calle} {sede.direccion.numero}, {sede.direccion.localidad}
          </p>
          <p>
            {sede.contacto.telefono} · {sede.contacto.email} · Responsable:{' '}
            {sede.contacto.responsable}
          </p>
          <p>Horario de hoy: {textoHorarioDelDia(sede.horarios, diaSemanaISO())}</p>
          {sede.excepciones.length > 0 && (
            <>
              <h3 className={estilos.subtitulo}>Próximos cierres</h3>
              <ul>
                {sede.excepciones.slice(0, 3).map((e) => (
                  <li key={e.id}>
                    {formatearFecha(e.fecha)}
                    {e.tipo === 'CIERRE_PARCIAL'
                      ? ` (${e.hora_desde}–${e.hora_hasta})`
                      : ' (todo el día)'}
                    {e.motivo ? `: ${e.motivo}` : ''}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </Card>
  );
}

export default function InicioBibliotecario({ usuario }) {
  return (
    <div className={estilos.pagina}>
      <MiSede sedeId={usuario.sede_id} />
      <SedesDeLaRed
        titulo="Otras sedes de la red"
        filtros={{ estado: 'ACTIVA' }}
        excluirId={usuario.sede_id}
      />
    </div>
  );
}
