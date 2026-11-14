import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  ErrorState,
  PageHeader,
  Skeleton,
  StatCard,
  Tabs,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { MOTIVOS_DE_INHABILITACION, TIPOS_DE_BAJA } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import AccionesSocio from '../components/AccionesSocio.jsx';
import EstadoSocioBadge from '../components/EstadoSocioBadge.jsx';
import HistorialSocio from '../components/HistorialSocio.jsx';
import { SolicitarReactivacionDialog } from '../components/SocioDialogs.jsx';
import { useSocio } from '../hooks/useSocios.js';

function Situacion({ situacion }) {
  return (
    <div className={inicio.tarjetas}>
      <StatCard etiqueta="Préstamos en curso" valor={situacion.prestamos_activos} />
      <StatCard etiqueta="Préstamos vencidos" valor={situacion.prestamos_vencidos} />
      <StatCard etiqueta="Multas pendientes" valor={situacion.multas_pendientes} />
      <StatCard etiqueta="Reservas activas" valor={situacion.reservas_activas} />
    </div>
  );
}

function Datos({ socio }) {
  return (
    <div className={estilos.datos}>
      <Card titulo="Datos personales">
        <dl className={estilos.definiciones}>
          <dt>Documento</dt>
          <dd>
            {socio.tipo_documento} {socio.nro_documento}
          </dd>
          <dt>Fecha de nacimiento</dt>
          <dd>{socio.fecha_nacimiento ? formatearFecha(socio.fecha_nacimiento) : 'Sin dato'}</dd>
          <dt>Sede de alta</dt>
          <dd>{socio.sede_alta}</dd>
        </dl>
      </Card>
      <Card titulo="Contacto">
        <dl className={estilos.definiciones}>
          <dt>Correo</dt>
          <dd>{socio.email ?? 'Sin dato'}</dd>
          <dt>Teléfono</dt>
          <dd>{socio.telefono ?? 'Sin dato'}</dd>
          <dt>Domicilio</dt>
          <dd>{socio.domicilio ?? 'Sin dato'}</dd>
        </dl>
      </Card>
      <Card titulo="Cuenta de acceso">
        <p style={{ margin: 0 }}>
          {socio.cuenta ? (
            <>
              Usuario <span className="mono">{socio.cuenta.username}</span>
            </>
          ) : (
            'Todavía no tiene cuenta para ingresar al sistema.'
          )}
        </p>
      </Card>
      {socio.creado_por && (
        <Card titulo="Auditoría">
          <dl className={estilos.definiciones}>
            <dt>Alta</dt>
            <dd>
              {formatearFechaHora(socio.fecha_alta)} · {socio.creado_por.nombre}
            </dd>
            {socio.actualizado_por && (
              <>
                <dt>Última modificación</dt>
                <dd>
                  {formatearFechaHora(socio.actualizado_en)} · {socio.actualizado_por.nombre}
                </dd>
              </>
            )}
          </dl>
        </Card>
      )}
    </div>
  );
}

/** Estado actual y por qué (inhabilitación o baja); al propio socio le dice cómo seguir. */
function AvisoDeEstado({ socio, propio }) {
  if (socio.estado === 'BAJA') {
    const tipo = TIPOS_DE_BAJA[socio.tipo_baja] ?? socio.tipo_baja;
    return (
      <Alert tono="info">
        Dado de baja el {formatearFechaHora(socio.fecha_baja)} ({tipo}). Motivo: {socio.motivo_baja}
        {socio.solicitud &&
          ` · Solicitud de reactivación pendiente desde el ${formatearFechaHora(socio.solicitud.fecha)}${socio.solicitud.mensaje ? `: «${socio.solicitud.mensaje}»` : ''}.`}
        {socio.motivo_administrativo &&
          ` Tiene una inhabilitación administrativa que sigue vigente si se reactiva.`}
      </Alert>
    );
  }
  if (socio.estado !== 'INHABILITADO') return null;
  const causas = socio.causas_inhabilitacion.map((c) => MOTIVOS_DE_INHABILITACION[c] ?? c);
  const automaticas = socio.causas_inhabilitacion.some((c) => c !== 'ADMINISTRATIVA');
  return (
    <Alert tono="warning">
      No puede pedir préstamos ni hacer reservas. Causas: {causas.join(', ')}.
      {socio.motivo_administrativo && ` Motivo administrativo: ${socio.motivo_administrativo}`}
      {propio &&
        automaticas &&
        ' Para habilitarte, devolvé el material vencido y saldá las multas en el mostrador de cualquier sede: el sistema te habilita solo.'}
    </Alert>
  );
}

/** Lo que el socio dado de baja puede hacer desde su cuenta: pedir volver. */
function PedirReactivacion({ socio }) {
  const [abierto, setAbierto] = useState(false);
  if (socio.estado !== 'BAJA' || !socio.reactivable || socio.solicitud) return null;
  return (
    <>
      <p style={{ margin: 0 }}>
        <Button onClick={() => setAbierto(true)}>Solicitar la reactivación</Button>
      </p>
      {abierto && <SolicitarReactivacionDialog socio={socio} onCerrar={() => setAbierto(false)} />}
    </>
  );
}

/**
 * Ficha del socio: datos, situación en la red y acciones según el rol. En «Mis datos» el socio
 * llega con `socioId` (el de su sesión) en lugar del id de la ruta.
 */
export default function SocioDetallePage({ socioId }) {
  const { id: idDeRuta } = useParams();
  const id = socioId ?? idDeRuta;
  const { usuario, tienePermiso } = useSesion();
  const { data: socio, isPending, error, refetch } = useSocio(id);
  const [params, setParams] = useSearchParams();
  const esPersonal = tienePermiso(PERMISOS.SOCIO_LEER);
  const propio = usuario?.socio_id === Number(id);
  const titulo = propio && !esPersonal ? 'Mis datos' : 'Socio';
  useTituloDePagina(socio ? `${socio.nombre} ${socio.apellido}` : titulo);
  const migas = esPersonal
    ? [{ texto: 'Socios', to: '/socios' }, { texto: socio?.numero_socio ?? 'Socio' }]
    : [{ texto: 'Mis datos' }];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo={titulo} migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
        {esPersonal && (
          <p>
            <Button to="/socios" variante="secondary">
              Volver a socios
            </Button>
          </p>
        )}
      </>
    );
  }

  return (
    <>
      <PageHeader
        titulo={`${socio.nombre} ${socio.apellido}`}
        descripcion={
          <>
            Socio <span className="mono">{socio.numero_socio}</span>{' '}
            <EstadoSocioBadge socio={socio} />
          </>
        }
        migas={<Breadcrumb items={migas} />}
        acciones={esPersonal && <AccionesSocio socio={socio} />}
      />
      <Tabs
        tabs={[
          {
            id: 'datos',
            titulo: 'Datos',
            contenido: (
              <div className={inicio.pagina}>
                <AvisoDeEstado socio={socio} propio={propio && !esPersonal} />
                {propio && !esPersonal && <PedirReactivacion socio={socio} />}
                <Situacion situacion={socio.situacion} />
                <Datos socio={socio} />
                {!esPersonal && (
                  <p className={inicio.detalle}>
                    Si algún dato no es correcto, pida la corrección en el mostrador de cualquier
                    sede.
                  </p>
                )}
              </div>
            ),
          },
          {
            id: 'historial',
            titulo: 'Historial',
            contenido: <HistorialSocio socioId={socio.id} />,
          },
        ]}
        activa={params.get('tab') === 'historial' ? 'historial' : 'datos'}
        onCambiar={(tab) => setParams(tab === 'datos' ? {} : { tab }, { replace: true })}
      />
    </>
  );
}
