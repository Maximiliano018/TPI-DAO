import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  ConfirmDialog,
  ErrorState,
  PageHeader,
  Skeleton,
  Table,
  Textarea,
  Timeline,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_FISICOS, MOTIVOS_DE_REMITO, estadoDe } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS, ROLES } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import {
  useAnularRemito,
  useAvanzarRemito,
  useMarcarExtraviado,
  useRemito,
} from '../../prestamos/hooks/usePrestamos.js';
import RecepcionDialog from '../components/RecepcionDialog.jsx';

const PASOS = {
  GENERADO: { accion: 'empaquetar', texto: 'Empaquetar', listo: 'Remito empaquetado' },
  EMPAQUETADO: {
    accion: 'despachar',
    texto: 'Despachar',
    listo: 'Remito despachado: los ejemplares quedan en tránsito',
  },
  DESPACHADO: { accion: 'en-transito', texto: 'Marcar en tránsito', listo: 'Remito en tránsito' },
};
const RESULTADOS = {
  RECIBIDO: 'Recibido',
  DANADO: 'Dañado',
  DESTRUIDO: 'Destruido',
  FALTANTE: 'No llegó',
};

const TIPOS_DE_INCIDENCIA = { EXTRAVIO: 'Extravío', DANIO: 'Daño', DESTRUCCION: 'Destrucción' };

/**
 * Incidencias del remito. Responde la sede origen, que despachó el envío; se muestra quién lo
 * despachó y quién la registró. Un extravío resuelto indica cuándo apareció el ejemplar.
 */
function Incidencias({ incidencias, lineas }) {
  const codigo = (id) => lineas.find((l) => l.ejemplar_id === id)?.codigo_ejemplar ?? id;
  return (
    <ul className={inicio.lista}>
      {incidencias.map((i) => (
        <li key={i.id ?? `${i.ejemplar_id}-${i.tipo}`} className={inicio.elemento}>
          <span>
            <strong>{TIPOS_DE_INCIDENCIA[i.tipo]}</strong> de{' '}
            <span className="mono">{codigo(i.ejemplar_id)}</span>: {i.descripcion}
            <br />
            Responsable: {i.sede_responsable?.nombre ?? '—'}
            {i.despachado_por && ` (despachó ${i.despachado_por.nombre})`} · registró{' '}
            {i.usuario?.nombre ?? 'Sistema'} el {formatearFechaHora(i.fecha)}
            {i.resuelta_en && (
              <>
                <br />
                Resuelta el {formatearFechaHora(i.resuelta_en)}: {i.resolucion}
              </>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Avance del ciclo (empaquetar, despachar, en tránsito) con su confirmación. */
function Avanzar({ remito, paso, onCerrar }) {
  const avanzar = useAvanzarRemito();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`${paso.texto} ${remito.numero}`}
      textoConfirmar={paso.texto}
      procesando={avanzar.isPending}
      onConfirmar={() =>
        avanzar.mutate(
          { id: remito.id, accion: paso.accion },
          {
            onSuccess: () => {
              mostrar(paso.listo);
              onCerrar();
            },
            onError: setFallo,
          },
        )
      }
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** Anulación o extravío: piden un motivo de 5 a 300 caracteres. */
function ConMotivo({ remito, titulo, descripcion, texto, mutacion, listo, onCerrar }) {
  const { mostrar } = useToast();
  const [motivo, setMotivo] = useState('');
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`${titulo} ${remito.numero}`}
      descripcion={descripcion}
      textoConfirmar={texto}
      peligro
      procesando={mutacion.isPending}
      deshabilitarConfirmar={motivo.trim().length < 5}
      onConfirmar={() =>
        mutacion.mutate(
          { id: remito.id, motivo },
          {
            onSuccess: () => {
              mostrar(listo);
              onCerrar();
            },
            onError: setFallo,
          },
        )
      }
      onCancelar={onCerrar}
    >
      <Textarea
        etiqueta="Motivo"
        requerido
        rows={2}
        ayuda="Entre 5 y 300 caracteres."
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

function Acciones({ remito }) {
  const { usuario, tienePermiso } = useSesion();
  const [dialogo, setDialogo] = useState(null);
  const anular = useAnularRemito();
  const extraviar = useMarcarExtraviado();
  const opera = tienePermiso(PERMISOS.REMITO_OPERAR);
  const esOrigen = opera && usuario.sede_id === remito.sede_origen_id;
  const esDestino = opera && usuario.sede_id === remito.sede_destino_id;
  const enViaje = ['DESPACHADO', 'EN_TRANSITO'].includes(remito.estado);
  const puedeExtraviar =
    tienePermiso(PERMISOS.REMITO_EXTRAVIO) &&
    enViaje &&
    (usuario.rol === ROLES.ADMIN || esOrigen || esDestino);
  const paso = PASOS[remito.estado];
  const cerrar = () => setDialogo(null);
  return (
    <>
      {esOrigen && paso && <Button onClick={() => setDialogo('avanzar')}>{paso.texto}</Button>}
      {esDestino && enViaje && <Button onClick={() => setDialogo('recibir')}>Recibir</Button>}
      {esOrigen &&
        remito.motivo !== 'RETORNO' &&
        ['GENERADO', 'EMPAQUETADO'].includes(remito.estado) && (
          <Button variante="danger" onClick={() => setDialogo('anular')}>
            Anular
          </Button>
        )}
      {puedeExtraviar && (
        <Button variante="danger" onClick={() => setDialogo('extraviado')}>
          Marcar extraviado
        </Button>
      )}
      {dialogo === 'avanzar' && <Avanzar remito={remito} paso={paso} onCerrar={cerrar} />}
      {dialogo === 'recibir' && <RecepcionDialog remito={remito} onCerrar={cerrar} />}
      {dialogo === 'anular' && (
        <ConMotivo
          remito={remito}
          titulo="Anular"
          descripcion="Los ejemplares vuelven a estar disponibles y se cancelan los préstamos del envío."
          texto="Anular remito"
          mutacion={anular}
          listo="Remito anulado"
          onCerrar={cerrar}
        />
      )}
      {dialogo === 'extraviado' && (
        <ConMotivo
          remito={remito}
          titulo="Marcar extraviado"
          descripcion="Solo si pasó el plazo máximo de tránsito. Los ejemplares se dan de baja con una incidencia."
          texto="Marcar extraviado"
          mutacion={extraviar}
          listo="Remito marcado como extraviado"
          onCerrar={cerrar}
        />
      )}
    </>
  );
}

/** Ficha del remito: detalle por ejemplar, trazabilidad e incidencias. */
export default function RemitoDetallePage() {
  const { id } = useParams();
  const { data: remito, isPending, error, refetch } = useRemito(id);
  useTituloDePagina(remito?.numero ?? 'Remito');
  const migas = [{ texto: 'Remitos', to: '/remitos' }, { texto: remito?.numero ?? 'Remito' }];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Remito" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
      </>
    );
  }

  const columnas = [
    {
      clave: 'codigo',
      titulo: 'Ejemplar',
      render: (l) => (
        <Link to={`/ejemplares/${l.ejemplar_id}`} className="mono">
          {l.codigo_ejemplar}
        </Link>
      ),
    },
    { clave: 'libro', titulo: 'Libro' },
    {
      clave: 'prestamo',
      titulo: 'Préstamo',
      render: (l) => (l.prestamo_id ? <Link to={`/prestamos/${l.prestamo_id}`}>Ver</Link> : '—'),
    },
    { clave: 'salida', titulo: 'Salió', render: (l) => ESTADOS_FISICOS[l.estado_fisico_salida] },
    {
      clave: 'llegada',
      titulo: 'Llegó',
      render: (l) => {
        if (!l.resultado) return '—';
        if (!l.estado_fisico_llegada) return RESULTADOS[l.resultado];
        return `${RESULTADOS[l.resultado]} (${ESTADOS_FISICOS[l.estado_fisico_llegada]})`;
      },
    },
  ];

  return (
    <>
      <PageHeader
        titulo={remito.numero}
        descripcion={
          <>
            {MOTIVOS_DE_REMITO[remito.motivo]}: {remito.sede_origen} → {remito.sede_destino}{' '}
            <EstadoBadge entidad="remito" estado={remito.estado} />
          </>
        }
        migas={<Breadcrumb items={migas} />}
        acciones={<Acciones remito={remito} />}
      />
      <div className={inicio.pagina}>
        {remito.atrasado && (
          <Alert tono="warning">
            Atrasado: tenía que despacharse hasta el {formatearFecha(remito.despachar_hasta)}. Si no
            va a salir, anúlelo para liberar los ejemplares.
          </Alert>
        )}
        {remito.incidencias.length > 0 && (
          <Card titulo="Incidencias">
            <Incidencias incidencias={remito.incidencias} lineas={remito.lineas} />
          </Card>
        )}
        <Card titulo="Ejemplares">
          <Table
            etiqueta="Detalle del remito"
            columnas={columnas}
            filas={remito.lineas}
            idDe={(l) => l.ejemplar_id}
          />
        </Card>
        <div className={estilos.datos}>
          <Card titulo="Fechas">
            <dl className={estilos.definiciones}>
              <dt>Generado</dt>
              <dd>{formatearFechaHora(remito.fecha_generacion)}</dd>
              <dt>Despachado</dt>
              <dd>{remito.fecha_despacho ? formatearFechaHora(remito.fecha_despacho) : '—'}</dd>
              <dt>Recibido</dt>
              <dd>{remito.fecha_recepcion ? formatearFechaHora(remito.fecha_recepcion) : '—'}</dd>
              {remito.observaciones && (
                <>
                  <dt>Observaciones</dt>
                  <dd>{remito.observaciones}</dd>
                </>
              )}
            </dl>
          </Card>
          <Card titulo="Trazabilidad">
            <Timeline
              etiqueta="Movimientos del remito"
              items={[...remito.movimientos].reverse().map((m, i) => ({
                id: i,
                titulo: estadoDe('remito', m.estado_nuevo).texto,
                meta: `${m.usuario?.nombre ?? 'Sistema'} · ${formatearFechaHora(m.fecha_hora)}`,
                contenido: m.observacion && <p style={{ margin: 0 }}>{m.observacion}</p>,
              }))}
            />
          </Card>
        </div>
      </div>
    </>
  );
}
