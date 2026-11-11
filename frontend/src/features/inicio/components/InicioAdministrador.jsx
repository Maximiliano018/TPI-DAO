import { Button, StatCard } from '../../../components/index.js';
import { useResumenSedes } from '../../sedes/hooks/useSedes.js';
import SedesDeLaRed from './SedesDeLaRed.jsx';
import estilos from './Inicio.module.css';

export default function InicioAdministrador() {
  const { data, isPending, error, refetch } = useResumenSedes();
  const comunes = { cargando: isPending, error, onReintentar: refetch };
  return (
    <div className={estilos.pagina}>
      <div className={estilos.tarjetas}>
        <StatCard
          etiqueta="Sedes activas"
          valor={data?.activas}
          to="/sedes?estado=ACTIVA"
          {...comunes}
        />
        <StatCard
          etiqueta="Sedes en baja"
          valor={data?.en_baja}
          to="/sedes?estado=BAJA"
          {...comunes}
        />
        <StatCard etiqueta="Total de sedes" valor={data?.total} to="/sedes" {...comunes} />
      </div>
      <div className={estilos.acciones}>
        <Button to="/sedes/nueva">Nueva sede</Button>
        <Button to="/sedes" variante="secondary">
          Sedes
        </Button>
      </div>
      <SedesDeLaRed titulo="Sedes de la red" mostrarEstado />
    </div>
  );
}
