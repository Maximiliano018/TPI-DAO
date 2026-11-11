import { zodResolver } from '@hookform/resolvers/zod';
import { useId, useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  Alert,
  Button,
  ConfirmDialog,
  Input,
  Modal,
  Select,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../../../utils/errores.js';
import { formatearFecha } from '../../../utils/formato.js';
import { esquemaExcepcion } from '../esquema.js';
import { useAgregarExcepciones, useQuitarExcepcion } from '../hooks/useSedesMutaciones.js';
import estilos from './Sedes.module.css';

function textoDeExcepcion(e) {
  return e.tipo === 'CIERRE_TOTAL'
    ? 'Cierre total'
    : `Cierre parcial de ${e.hora_desde} a ${e.hora_hasta}`;
}

/** Alta de un cierre por fecha o rango (hasta 31 días). */
function ExcepcionDialog({ sede, onCerrar }) {
  const idFormulario = useId();
  const agregar = useAgregarExcepciones(sede.id);
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaExcepcion),
    defaultValues: {
      fecha_desde: '',
      fecha_hasta: '',
      tipo: 'CIERRE_TOTAL',
      hora_desde: '',
      hora_hasta: '',
      motivo: '',
    },
  });
  const parcial = watch('tipo') === 'CIERRE_PARCIAL';

  function enviar(datos) {
    setFallo(null);
    agregar.mutate(
      {
        fecha_desde: datos.fecha_desde,
        fecha_hasta: datos.fecha_hasta || null,
        tipo: datos.tipo,
        hora_desde: parcial ? datos.hora_desde : null,
        hora_hasta: parcial ? datos.hora_hasta : null,
        motivo: datos.motivo.trim() || null,
      },
      {
        onSuccess: (creadas) => {
          mostrar(creadas.length === 1 ? 'Cierre agregado' : `${creadas.length} cierres agregados`);
          onCerrar();
        },
        onError: (error) => {
          const porCampo = erroresPorCampo(error);
          const campo = Object.keys(porCampo).find((c) => c in datos);
          if (campo) setError(campo, { message: porCampo[campo] });
          else setFallo(error);
        },
      },
    );
  }

  return (
    <Modal
      titulo="Agregar cierre"
      onCerrar={onCerrar}
      bloqueado={agregar.isPending}
      acciones={
        <>
          <Button variante="secondary" onClick={onCerrar} disabled={agregar.isPending}>
            Cancelar
          </Button>
          <Button type="submit" form={idFormulario} cargando={agregar.isPending}>
            Agregar cierre
          </Button>
        </>
      }
    >
      <form
        id={idFormulario}
        onSubmit={handleSubmit(enviar)}
        noValidate
        className={estilos.seccion}
      >
        {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
        <Input
          etiqueta="Fecha (o primer día)"
          type="date"
          requerido
          data-autofocus
          error={errors.fecha_desde?.message}
          {...register('fecha_desde')}
        />
        <Input
          etiqueta="Último día (opcional)"
          type="date"
          ayuda="Para cerrar varios días seguidos, hasta 31."
          error={errors.fecha_hasta?.message}
          {...register('fecha_hasta')}
        />
        <Select etiqueta="Tipo de cierre" requerido {...register('tipo')}>
          <option value="CIERRE_TOTAL">Cierre total</option>
          <option value="CIERRE_PARCIAL">Cierre parcial</option>
        </Select>
        {parcial && (
          <div className={estilos.grupo}>
            <Input
              etiqueta="Cerrada desde"
              type="time"
              requerido
              error={errors.hora_desde?.message}
              {...register('hora_desde')}
            />
            <Input
              etiqueta="Cerrada hasta"
              type="time"
              requerido
              error={errors.hora_hasta?.message}
              {...register('hora_hasta')}
            />
          </div>
        )}
        <Textarea
          etiqueta="Motivo (opcional)"
          rows={2}
          error={errors.motivo?.message}
          {...register('motivo')}
        />
      </form>
    </Modal>
  );
}

/** Cierres vigentes de la sede; el administrador puede agregarlos y quitarlos. */
export default function ExcepcionesHorario({ sede, puedeEditar }) {
  const [dialogo, setDialogo] = useState(null);
  const [quitando, setQuitando] = useState(null);
  const [fallo, setFallo] = useState(null);
  const quitar = useQuitarExcepcion(sede.id);
  const { mostrar } = useToast();

  return (
    <div className={estilos.seccion}>
      {puedeEditar && (
        <div>
          <Button variante="secondary" onClick={() => setDialogo('agregar')}>
            Agregar cierre
          </Button>
        </div>
      )}
      {sede.excepciones.length === 0 ? (
        <p style={{ margin: 0 }}>No hay cierres cargados para los próximos días.</p>
      ) : (
        <ul className={estilos.excepciones} aria-label="Cierres vigentes">
          {sede.excepciones.map((e) => (
            <li key={e.id} className={estilos.excepcion}>
              <span>
                <strong>{formatearFecha(e.fecha)}</strong> · {textoDeExcepcion(e)}
                {e.motivo && ` · ${e.motivo}`}
              </span>
              {puedeEditar && (
                <Button
                  variante="link"
                  tamano="sm"
                  aria-label={`Quitar el cierre del ${formatearFecha(e.fecha)}`}
                  onClick={() => {
                    setFallo(null);
                    setQuitando(e);
                  }}
                >
                  Quitar
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {dialogo === 'agregar' && <ExcepcionDialog sede={sede} onCerrar={() => setDialogo(null)} />}
      {quitando && (
        <ConfirmDialog
          titulo="Quitar cierre"
          descripcion={`Se quitará el cierre del ${formatearFecha(quitando.fecha)}. La sede volverá a atender con su horario habitual.`}
          textoConfirmar="Quitar cierre"
          peligro
          procesando={quitar.isPending}
          onConfirmar={() =>
            quitar.mutate(quitando.id, {
              onSuccess: () => {
                mostrar('Cierre quitado');
                setQuitando(null);
              },
              onError: setFallo,
            })
          }
          onCancelar={() => setQuitando(null)}
        >
          {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
        </ConfirmDialog>
      )}
    </div>
  );
}
