import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
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
  Select,
  Skeleton,
  Textarea,
  Timeline,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_FISICOS, estadoDe } from '../../../utils/estados.js';
import { formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS, ROLES } from '../../../utils/roles.js';
import { esquemaMotivo } from '../../socios/esquema.js';
import estilos from '../../sedes/components/Sedes.module.css';
import inicio from '../../inicio/components/Inicio.module.css';
import EstadoEjemplarBadge from '../components/EstadoEjemplarBadge.jsx';
import { esquemaEstadoFisico } from '../esquema.js';
import {
  useBajaEjemplar,
  useEjemplar,
  useModificarEjemplar,
  useRepararEjemplar,
} from '../hooks/useCatalogo.js';

function EditarDialog({ ejemplar, onCerrar }) {
  const modificar = useModificarEjemplar();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaEstadoFisico),
    defaultValues: {
      estado_fisico: ejemplar.estado_fisico,
      observaciones: ejemplar.observaciones ?? '',
    },
  });
  const confirmar = handleSubmit((datos) =>
    modificar.mutate(
      {
        id: ejemplar.id,
        estado_fisico: datos.estado_fisico,
        observaciones: datos.observaciones || null,
        version: ejemplar.version,
      },
      {
        onSuccess: () => {
          mostrar('Ejemplar guardado');
          onCerrar();
        },
        onError: setFallo,
      },
    ),
  );
  return (
    <ConfirmDialog
      titulo={`Editar ${ejemplar.codigo_inventario}`}
      descripcion="La disponibilidad no se edita: la cambian los préstamos, envíos y devoluciones."
      textoConfirmar="Guardar"
      procesando={modificar.isPending}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <Select etiqueta="Estado físico" requerido {...register('estado_fisico')}>
        {Object.entries(ESTADOS_FISICOS).map(([valor, texto]) => (
          <option key={valor} value={valor}>
            {texto}
          </option>
        ))}
      </Select>
      <Textarea
        etiqueta="Observaciones"
        rows={2}
        error={errors.observaciones?.message}
        {...register('observaciones')}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

function BajaDialog({ ejemplar, onCerrar }) {
  const baja = useBajaEjemplar();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaMotivo),
    defaultValues: { motivo: '' },
  });
  const confirmar = handleSubmit(({ motivo }) =>
    baja.mutate(
      { id: ejemplar.id, motivo, version: ejemplar.version },
      {
        onSuccess: () => {
          mostrar('Ejemplar dado de baja');
          onCerrar();
        },
        onError: setFallo,
      },
    ),
  );
  return (
    <ConfirmDialog
      titulo={`Dar de baja ${ejemplar.codigo_inventario}`}
      descripcion="Deja de ofrecerse en la red. Se conserva su historial."
      textoConfirmar="Dar de baja"
      peligro
      procesando={baja.isPending}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <Textarea
        etiqueta="Motivo"
        requerido
        rows={3}
        ayuda="Entre 5 y 300 caracteres."
        error={errors.motivo?.message}
        {...register('motivo')}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

function RepararDialog({ ejemplar, onCerrar }) {
  const reparar = useRepararEjemplar();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Marcar ${ejemplar.codigo_inventario} como reparado`}
      descripcion="Sale de revisión, queda disponible y con estado físico «Regular»."
      textoConfirmar="Marcar como reparado"
      procesando={reparar.isPending}
      onConfirmar={() =>
        reparar.mutate(
          { id: ejemplar.id, version: ejemplar.version },
          {
            onSuccess: () => {
              mostrar('Ejemplar reparado');
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

/** Ficha de un ejemplar con su historial de estados (solo personal). */
export default function EjemplarDetallePage() {
  const { id } = useParams();
  const { usuario, tienePermiso } = useSesion();
  const { data: ejemplar, isPending, error, refetch } = useEjemplar(id);
  const [dialogo, setDialogo] = useState(null);
  useTituloDePagina(ejemplar?.codigo_inventario ?? 'Ejemplar');
  const migas = [
    { texto: 'Ejemplares', to: '/ejemplares' },
    { texto: ejemplar?.codigo_inventario ?? 'Ejemplar' },
  ];

  if (isPending) return <Skeleton alto={200} />;
  if (error) {
    return (
      <>
        <PageHeader titulo="Ejemplar" migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
      </>
    );
  }

  const esDeSuSede =
    usuario.rol === ROLES.ADMIN || usuario.sede_id === ejemplar.sede_propietaria_id;
  const gestiona = tienePermiso(PERMISOS.EJEMPLAR_ADMINISTRAR) && esDeSuSede;
  const cerrar = () => setDialogo(null);
  return (
    <>
      <PageHeader
        titulo={ejemplar.codigo_inventario}
        descripcion={
          <>
            <Link to={`/catalogo/${ejemplar.libro_id}`}>{ejemplar.libro}</Link>{' '}
            <EstadoEjemplarBadge estado={ejemplar.estado} />
          </>
        }
        migas={<Breadcrumb items={migas} />}
        acciones={
          gestiona &&
          ejemplar.estado !== 'BAJA' && (
            <>
              <Button variante="secondary" onClick={() => setDialogo('editar')}>
                Editar
              </Button>
              {ejemplar.estado === 'EN_REVISION' && (
                <Button variante="secondary" onClick={() => setDialogo('reparar')}>
                  Marcar como reparado
                </Button>
              )}
              {['DISPONIBLE', 'EN_REVISION'].includes(ejemplar.estado) && (
                <Button variante="danger" onClick={() => setDialogo('baja')}>
                  Dar de baja
                </Button>
              )}
            </>
          )
        }
      />
      <div className={inicio.pagina}>
        {ejemplar.estado === 'BAJA' && (
          <Alert tono="info">
            Dado de baja el {formatearFechaHora(ejemplar.fecha_baja)}. Motivo:{' '}
            {ejemplar.motivo_baja}
          </Alert>
        )}
        <div className={estilos.datos}>
          <Card titulo="Datos">
            <dl className={estilos.definiciones}>
              <dt>Sede propietaria</dt>
              <dd>{ejemplar.sede_propietaria}</dd>
              <dt>Está en</dt>
              <dd>{ejemplar.sede_actual}</dd>
              <dt>Estado físico</dt>
              <dd>{ESTADOS_FISICOS[ejemplar.estado_fisico]}</dd>
              <dt>Observaciones</dt>
              <dd>{ejemplar.observaciones ?? 'Sin observaciones'}</dd>
            </dl>
          </Card>
          <Card titulo="Historial">
            <Timeline
              etiqueta="Historial del ejemplar"
              items={[...ejemplar.historial].reverse().map((m, i) => ({
                id: i,
                titulo: estadoDe('ejemplar', m.estado_nuevo).texto,
                meta: `${m.usuario?.nombre ?? 'Sistema'} · ${formatearFechaHora(m.fecha_hora)}`,
                contenido: m.observacion && <p style={{ margin: 0 }}>{m.observacion}</p>,
              }))}
            />
          </Card>
        </div>
      </div>
      {dialogo === 'editar' && <EditarDialog ejemplar={ejemplar} onCerrar={cerrar} />}
      {dialogo === 'baja' && <BajaDialog ejemplar={ejemplar} onCerrar={cerrar} />}
      {dialogo === 'reparar' && <RepararDialog ejemplar={ejemplar} onCerrar={cerrar} />}
    </>
  );
}
