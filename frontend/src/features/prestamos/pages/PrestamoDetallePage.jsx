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
  Input,
  PageHeader,
  Skeleton,
  Timeline,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { MOTIVOS_DE_REMITO, TIPOS_DE_PRESTAMO, estadoDe } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoBadge from '../components/EstadoBadge.jsx';
import {
  useCancelarPrestamo,
  useEntregarPrestamo,
  usePrestamo,
  useRenovarPrestamo,
} from '../hooks/usePrestamos.js';

/** Confirmación de una acción sobre el préstamo; muestra el error del servidor si falla. */
function Accion({
  titulo,
  descripcion,
  texto,
  mutacion,
  variables,
  listo,
  peligro,
  onCerrar,
  children,
}) {
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={titulo}
      descripcion={descripcion}
      textoConfirmar={texto}
      peligro={peligro}
      procesando={mutacion.isPending}
      onConfirmar={() => {
        setFallo(null);
        mutacion.mutate(variables(), {
          onSuccess: () => {
            mostrar(listo);
            onCerrar();
          },
          onError: setFallo,
        });
      }}
      onCancelar={onCerrar}
    >
      {children}
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

function Acciones({ prestamo }) {
  const { usuario, tienePermiso } = useSesion();
  const [dialogo, setDialogo] = useState(null);
  const [motivo, setMotivo] = useState('');
  const entregar = useEntregarPrestamo();
  const renovar = useRenovarPrestamo();
  const cancelar = useCancelarPrestamo();
  if (!tienePermiso(PERMISOS.PRESTAMO_REGISTRAR)) return null;
  const enDestino = usuario.sede_id === prestamo.sede_destino_id;
  const enSede = enDestino || usuario.sede_id === prestamo.sede_origen_id;
  const { estado, tipo } = prestamo;
  const puedeEntregar =
    enDestino &&
    ((estado === 'SOLICITADO' && tipo === 'LOCAL') ||
      (estado === 'EN_ENVIO' && tipo === 'INTERBIBLIOTECARIO'));
  const cerrar = () => setDialogo(null);
  return (
    <>
      {puedeEntregar && <Button onClick={() => setDialogo('entregar')}>Entregar al socio</Button>}
      {enDestino && estado === 'ACTIVO' && (
        <Button variante="secondary" onClick={() => setDialogo('renovar')}>
          Renovar
        </Button>
      )}
      {enSede && ['SOLICITADO', 'EN_ENVIO'].includes(estado) && (
        <Button variante="danger" onClick={() => setDialogo('cancelar')}>
          Cancelar
        </Button>
      )}
      {dialogo === 'entregar' && (
        <Accion
          titulo={`Entregar ${prestamo.codigo_ejemplar}`}
          descripcion="Empieza el plazo del préstamo desde hoy."
          texto="Entregar"
          mutacion={entregar}
          variables={() => prestamo.id}
          listo="Préstamo entregado"
          onCerrar={cerrar}
        />
      )}
      {dialogo === 'renovar' && (
        <Accion
          titulo={`Renovar ${prestamo.numero}`}
          descripcion="Suma un plazo al vencimiento actual, si no venció y nadie reservó el libro."
          texto="Renovar"
          mutacion={renovar}
          variables={() => prestamo.id}
          listo="Préstamo renovado"
          onCerrar={cerrar}
        />
      )}
      {dialogo === 'cancelar' && (
        <Accion
          titulo={`Cancelar ${prestamo.numero}`}
          descripcion={
            estado === 'EN_ENVIO'
              ? 'Si el ejemplar ya llegó, vuelve a su sede con un remito de retorno.'
              : 'El ejemplar vuelve a quedar disponible.'
          }
          texto="Cancelar préstamo"
          peligro
          mutacion={cancelar}
          variables={() => ({ id: prestamo.id, motivo: motivo || null })}
          listo="Préstamo cancelado"
          onCerrar={cerrar}
        >
          <Input
            etiqueta="Motivo (opcional)"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        </Accion>
      )}
    </>
  );
}

/** Ficha del préstamo: datos, plazo, remitos de ida y vuelta e historial. */
export default function PrestamoDetallePage() {
  const { id } = useParams();
  const { tienePermiso } = useSesion();
  const { data: prestamo, isPending, error, refetch } = usePrestamo(id);
  useTituloDePagina(prestamo?.numero ?? 'Préstamo');
  const esPersonal = tienePermiso(PERMISOS.PRESTAMO_LEER);
  const migas = [
    { texto: esPersonal ? 'Préstamos' : 'Mis préstamos', to: '/prestamos' },
    { texto: prestamo?.numero ?? 'Préstamo' },
  ];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Préstamo" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        titulo={prestamo.numero}
        descripcion={
          <>
            {prestamo.libro} · {TIPOS_DE_PRESTAMO[prestamo.tipo]}{' '}
            <EstadoBadge entidad="prestamo" estado={prestamo.estado} />
          </>
        }
        migas={<Breadcrumb items={migas} />}
        acciones={<Acciones prestamo={prestamo} />}
      />
      <div className={inicio.pagina}>
        {prestamo.estado === 'VENCIDO' && (
          <Alert tono="danger">
            Venció el {formatearFecha(prestamo.fecha_vencimiento)}. Al devolverlo se genera una
            multa por los días de atraso.
          </Alert>
        )}
        <div className={estilos.datos}>
          <Card titulo="Préstamo">
            <dl className={estilos.definiciones}>
              <dt>Socio</dt>
              <dd>
                {esPersonal ? (
                  <Link to={`/socios/${prestamo.socio_id}`}>{prestamo.socio}</Link>
                ) : (
                  prestamo.socio
                )}{' '}
                <span className="mono">{prestamo.numero_socio}</span>
              </dd>
              <dt>Ejemplar</dt>
              <dd>
                {esPersonal ? (
                  <Link to={`/ejemplares/${prestamo.ejemplar_id}`} className="mono">
                    {prestamo.codigo_ejemplar}
                  </Link>
                ) : (
                  <span className="mono">{prestamo.codigo_ejemplar}</span>
                )}
              </dd>
              <dt>Sale de</dt>
              <dd>{prestamo.sede_origen}</dd>
              <dt>Retira y devuelve en</dt>
              <dd>{prestamo.sede_destino}</dd>
            </dl>
          </Card>
          <Card titulo="Plazo">
            <dl className={estilos.definiciones}>
              <dt>Solicitado</dt>
              <dd>{formatearFechaHora(prestamo.fecha_solicitud)}</dd>
              <dt>Entregado</dt>
              <dd>
                {prestamo.fecha_inicio ? formatearFecha(prestamo.fecha_inicio) : 'Todavía no'}
              </dd>
              <dt>Vence</dt>
              <dd>
                {prestamo.fecha_vencimiento
                  ? formatearFecha(prestamo.fecha_vencimiento)
                  : 'Al entregarlo'}
              </dd>
              <dt>Renovaciones</dt>
              <dd>{prestamo.renovaciones}</dd>
            </dl>
          </Card>
          {prestamo.remitos.length > 0 && (
            <Card titulo="Envíos">
              <ul className={inicio.lista}>
                {prestamo.remitos.map((r) => (
                  <li key={r.id} className={inicio.elemento}>
                    <span>
                      {MOTIVOS_DE_REMITO[r.motivo]}:{' '}
                      {esPersonal ? (
                        <Link to={`/remitos/${r.id}`} className="mono">
                          {r.numero}
                        </Link>
                      ) : (
                        <span className="mono">{r.numero}</span>
                      )}
                    </span>
                    <EstadoBadge entidad="remito" estado={r.estado} />
                  </li>
                ))}
              </ul>
            </Card>
          )}
          <Card titulo="Historial">
            <Timeline
              etiqueta="Historial del préstamo"
              items={[...prestamo.historial].reverse().map((m, i) => ({
                id: i,
                titulo: estadoDe('prestamo', m.estado_nuevo).texto,
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
