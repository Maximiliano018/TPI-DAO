import { useLocation, useParams, useSearchParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  ErrorState,
  PageHeader,
  Skeleton,
  Tabs,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import AbiertaBadge from '../components/AbiertaBadge.jsx';
import AccionesSede from '../components/AccionesSede.jsx';
import EstadoSedeBadge from '../components/EstadoSedeBadge.jsx';
import ExcepcionesHorario from '../components/ExcepcionesHorario.jsx';
import HistorialSede from '../components/HistorialSede.jsx';
import HorarioSemanal from '../components/HorarioSemanal.jsx';
import estilos from '../components/Sedes.module.css';
import { useSede } from '../hooks/useSedes.js';

function Datos({ sede }) {
  return (
    <div className={estilos.datos}>
      <Card titulo="Domicilio">
        <dl className={estilos.definiciones}>
          <dt>Calle</dt>
          <dd>
            {sede.direccion.calle} {sede.direccion.numero}
          </dd>
          <dt>Localidad</dt>
          <dd>{sede.direccion.localidad}</dd>
          <dt>Provincia</dt>
          <dd>{sede.direccion.provincia}</dd>
        </dl>
      </Card>
      <Card titulo="Contacto">
        <dl className={estilos.definiciones}>
          <dt>Teléfono</dt>
          <dd>{sede.contacto.telefono}</dd>
          <dt>Correo</dt>
          <dd>{sede.contacto.email}</dd>
          {sede.contacto.responsable && (
            <>
              <dt>Responsable</dt>
              <dd>{sede.contacto.responsable}</dd>
            </>
          )}
        </dl>
      </Card>
      {sede.baja && (
        <Card titulo="Baja de la sede">
          <dl className={estilos.definiciones}>
            <dt>Fecha</dt>
            <dd>{formatearFechaHora(sede.baja.fecha)}</dd>
            <dt>Motivo</dt>
            <dd>{sede.baja.motivo}</dd>
            <dt>Registrada por</dt>
            <dd>{sede.baja.usuario.nombre}</dd>
          </dl>
        </Card>
      )}
      {sede.creado_por && (
        <Card titulo="Auditoría">
          <dl className={estilos.definiciones}>
            <dt>Creada</dt>
            <dd>
              {formatearFechaHora(sede.creado_en)} · {sede.creado_por.nombre}
            </dd>
            <dt>Última modificación</dt>
            <dd>
              {formatearFechaHora(sede.actualizado_en)} · {sede.actualizado_por.nombre}
            </dd>
          </dl>
        </Card>
      )}
    </div>
  );
}

/** Detalle de una sede con pestañas Datos, Horarios e Historial (solo administrador). */
export default function SedeDetallePage() {
  const { id } = useParams();
  const { tienePermiso } = useSesion();
  const ubicacion = useLocation();
  const [params, setParams] = useSearchParams();
  const { data: sede, isPending, error, refetch } = useSede(id);
  useTituloDePagina(sede?.nombre ?? 'Sede');

  const puedeVerHistorial = tienePermiso(PERMISOS.SEDE_VER_HISTORIAL);
  const puedeEditar = tienePermiso(PERMISOS.SEDE_ADMINISTRAR) && sede?.estado !== 'BAJA';
  const migas = [{ texto: 'Sedes', to: '/sedes' }, { texto: sede?.nombre ?? 'Sede' }];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Sede" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
        <p>
          <Button to="/sedes" variante="secondary">
            Volver a sedes
          </Button>
        </p>
      </>
    );
  }

  const pestanias = [
    { id: 'datos', titulo: 'Datos', contenido: <Datos sede={sede} /> },
    {
      id: 'horarios',
      titulo: 'Horarios',
      contenido: (
        <div className={estilos.seccion}>
          <Card titulo="Horario semanal">
            <HorarioSemanal horarios={sede.horarios} />
          </Card>
          <Card titulo="Cierres por fecha">
            <ExcepcionesHorario sede={sede} puedeEditar={puedeEditar} />
          </Card>
        </div>
      ),
    },
    ...(puedeVerHistorial
      ? [{ id: 'historial', titulo: 'Historial', contenido: <HistorialSede sedeId={sede.id} /> }]
      : []),
  ];
  const pedida = params.get('tab');
  const activa = pestanias.some((p) => p.id === pedida) ? pedida : 'datos';

  return (
    <>
      <PageHeader
        titulo={sede.nombre}
        migas={<Breadcrumb items={migas} />}
        acciones={
          <div className={estilos.acciones}>
            <AccionesSede sede={sede} />
          </div>
        }
      >
        <p style={{ margin: 0, display: 'flex', gap: 8, alignItems: 'center' }}>
          <span className={estilos.codigo}>{sede.codigo}</span>
          {sede.estado && <EstadoSedeBadge estado={sede.estado} />}
          {sede.estado !== 'BAJA' && <AbiertaBadge abierta={sede.abierta_ahora} />}
        </p>
      </PageHeader>
      {ubicacion.state?.aviso && <Alert tono="info">{ubicacion.state.aviso}</Alert>}
      <Tabs
        tabs={pestanias}
        activa={activa}
        onCambiar={(tab) => setParams(tab === 'datos' ? {} : { tab }, { replace: true })}
      />
    </>
  );
}
