import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  Alert,
  ConfirmDialog,
  Input,
  Select,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { TIPOS_DE_BAJA } from '../../../utils/estados.js';
import { esquemaCuenta, esquemaMotivo, esquemaSolicitud } from '../esquema.js';
import {
  useAprobarSolicitud,
  useBajaSocio,
  useCrearCuentaSocio,
  useInhabilitarSocio,
  useReactivarSocio,
  useRechazarSolicitud,
  useRehabilitarSocio,
  useSolicitarReactivacion,
} from '../hooks/useSocios.js';

const nombreDe = (socio) => `${socio.nombre} ${socio.apellido}`;

/** Diálogo con un motivo obligatorio (inhabilitación administrativa y baja). */
function DialogoConMotivo({
  titulo,
  descripcion,
  textoConfirmar,
  enviar,
  procesando,
  onCerrar,
  peligro = true,
  children,
}) {
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(esquemaMotivo), defaultValues: { motivo: '' } });
  const confirmar = handleSubmit(({ motivo }) => {
    setFallo(null);
    enviar(motivo, setFallo);
  });
  return (
    <ConfirmDialog
      titulo={titulo}
      descripcion={descripcion}
      textoConfirmar={textoConfirmar}
      peligro={peligro}
      procesando={procesando}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      {children}
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

export function InhabilitarSocioDialog({ socio, onCerrar }) {
  const inhabilitar = useInhabilitarSocio();
  const { mostrar } = useToast();
  return (
    <DialogoConMotivo
      titulo={`Inhabilitar a ${nombreDe(socio)}`}
      descripcion="No podrá pedir préstamos ni hacer reservas hasta que un administrador levante la inhabilitación. Los préstamos en curso siguen vigentes."
      textoConfirmar="Inhabilitar"
      procesando={inhabilitar.isPending}
      enviar={(motivo, alFallar) =>
        inhabilitar.mutate(
          { id: socio.id, motivo },
          {
            onSuccess: () => {
              mostrar('Socio inhabilitado');
              onCerrar();
            },
            onError: alFallar,
          },
        )
      }
      onCerrar={onCerrar}
    />
  );
}

const reservas = (n) => (n === 1 ? '1 reserva activa' : `${n} reservas activas`);

const AVISO_POR_TIPO = {
  A_PEDIDO: 'Puede pedir la reactivación desde su cuenta o en cualquier sede.',
  ADMINISTRATIVA: 'Solo un administrador puede reactivarlo.',
  FALLECIMIENTO: 'Es definitiva: no se puede reactivar y su cuenta de acceso se desactiva.',
};

/**
 * Baja con tipo y motivo. El bibliotecario solo registra la baja a pedido del socio; el
 * administrador elige además la administrativa o por fallecimiento.
 */
export function BajaSocioDialog({ socio, onCerrar, administra }) {
  const baja = useBajaSocio();
  const { mostrar } = useToast();
  const [tipo, setTipo] = useState('A_PEDIDO');
  const activas = socio.situacion?.reservas_activas ?? 0;
  const aviso = activas
    ? ` Tiene ${reservas(activas)}: se van a cancelar y los ejemplares pasan al siguiente en la cola.`
    : '';
  const tipos = administra ? Object.keys(TIPOS_DE_BAJA).reverse() : ['A_PEDIDO'];
  return (
    <DialogoConMotivo
      titulo={`Dar de baja a ${nombreDe(socio)}`}
      descripcion={`Solo se puede si no tiene préstamos en curso ni multas pendientes. Se conserva su historial.${aviso}`}
      textoConfirmar="Dar de baja"
      procesando={baja.isPending}
      enviar={(motivo, alFallar) =>
        baja.mutate(
          { id: socio.id, tipo, motivo },
          {
            onSuccess: ({ reservas_canceladas: canceladas }) => {
              mostrar(
                canceladas
                  ? `Socio dado de baja. Se cancelaron ${canceladas === 1 ? '1 reserva' : `${canceladas} reservas`}.`
                  : 'Socio dado de baja',
              );
              onCerrar();
            },
            onError: alFallar,
          },
        )
      }
      onCerrar={onCerrar}
    >
      <Select
        etiqueta="Tipo de baja"
        value={tipo}
        onChange={(e) => setTipo(e.target.value)}
        ayuda={AVISO_POR_TIPO[tipo]}
        disabled={tipos.length === 1}
      >
        {tipos.map((t) => (
          <option key={t} value={t}>
            {TIPOS_DE_BAJA[t]}
          </option>
        ))}
      </Select>
    </DialogoConMotivo>
  );
}

/** Confirmación simple que muestra el error del servidor si lo hay. */
function Confirmacion({ titulo, descripcion, textoConfirmar, mutacion, textoListo, id, onCerrar }) {
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={titulo}
      descripcion={descripcion}
      textoConfirmar={textoConfirmar}
      procesando={mutacion.isPending}
      onConfirmar={() => {
        setFallo(null);
        mutacion.mutate(id, {
          onSuccess: () => {
            mostrar(textoListo);
            onCerrar();
          },
          onError: setFallo,
        });
      }}
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

export function RehabilitarSocioDialog({ socio, onCerrar }) {
  const rehabilitar = useRehabilitarSocio();
  const administrativa = socio.motivo_inhabilitacion === 'ADMINISTRATIVA';
  return (
    <Confirmacion
      titulo={`Rehabilitar a ${nombreDe(socio)}`}
      descripcion={
        administrativa
          ? 'Se levanta la inhabilitación administrativa. Si tiene un préstamo vencido o una multa impaga, sigue inhabilitado por esa causa.'
          : 'Vuelve a quedar habilitado si ya no tiene préstamos vencidos ni multas impagas.'
      }
      textoConfirmar="Rehabilitar"
      mutacion={rehabilitar}
      textoListo="Socio rehabilitado"
      id={socio.id}
      onCerrar={onCerrar}
    />
  );
}

const VUELVE_SANCIONADO =
  ' Tenía una inhabilitación administrativa: vuelve inhabilitado hasta que un administrador la levante.';

function descripcionDeReactivacion(socio) {
  const base = 'Vuelve con su mismo número de socio e historial.';
  return socio.motivo_administrativo ? `${base}${VUELVE_SANCIONADO}` : base;
}

/** Reactivación en mostrador: el socio la pide y el personal la registra. */
export function ReactivarSocioDialog({ socio, onCerrar }) {
  const reactivar = useReactivarSocio();
  return (
    <Confirmacion
      titulo={`Reactivar a ${nombreDe(socio)}`}
      descripcion={descripcionDeReactivacion(socio)}
      textoConfirmar="Reactivar"
      mutacion={reactivar}
      textoListo="Socio reactivado"
      id={socio.id}
      onCerrar={onCerrar}
    />
  );
}

export function AprobarSolicitudDialog({ socio, onCerrar }) {
  const aprobar = useAprobarSolicitud();
  const mensaje = socio.solicitud?.mensaje;
  return (
    <Confirmacion
      titulo={`Aprobar la reactivación de ${nombreDe(socio)}`}
      descripcion={`${mensaje ? `Mensaje del socio: «${mensaje}». ` : ''}${descripcionDeReactivacion(socio)}`}
      textoConfirmar="Aprobar"
      mutacion={aprobar}
      textoListo="Solicitud aprobada: socio reactivado"
      id={socio.id}
      onCerrar={onCerrar}
    />
  );
}

export function RechazarSolicitudDialog({ socio, onCerrar }) {
  const rechazar = useRechazarSolicitud();
  const { mostrar } = useToast();
  return (
    <DialogoConMotivo
      titulo={`Rechazar la reactivación de ${nombreDe(socio)}`}
      descripcion="El socio sigue dado de baja y ve el motivo en su historial. Puede volver a pedirla."
      textoConfirmar="Rechazar"
      procesando={rechazar.isPending}
      enviar={(motivo, alFallar) =>
        rechazar.mutate(
          { id: socio.id, motivo },
          {
            onSuccess: () => {
              mostrar('Solicitud rechazada');
              onCerrar();
            },
            onError: alFallar,
          },
        )
      }
      onCerrar={onCerrar}
    />
  );
}

/** El socio dado de baja pide volver desde su cuenta, con un mensaje opcional. */
export function SolicitarReactivacionDialog({ socio, onCerrar }) {
  const solicitar = useSolicitarReactivacion();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(esquemaSolicitud), defaultValues: { mensaje: '' } });
  const confirmar = handleSubmit(({ mensaje }) => {
    setFallo(null);
    solicitar.mutate(
      { id: socio.id, mensaje: mensaje || null },
      {
        onSuccess: () => {
          mostrar('Solicitud enviada');
          onCerrar();
        },
        onError: setFallo,
      },
    );
  });
  return (
    <ConfirmDialog
      titulo="Solicitar la reactivación"
      descripcion="El personal de la biblioteca revisa tu pedido y lo aprueba o lo rechaza. Vas a ver la respuesta en tu historial."
      textoConfirmar="Enviar solicitud"
      procesando={solicitar.isPending}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <Textarea
        etiqueta="Mensaje (opcional)"
        rows={3}
        ayuda="Hasta 300 caracteres."
        error={errors.mensaje?.message}
        {...register('mensaje')}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** Alta de la cuenta con la que el socio entra a consultar y reservar. */
export function CrearCuentaDialog({ socio, onCerrar }) {
  const crear = useCrearCuentaSocio();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaCuenta),
    defaultValues: { username: '', password: '', confirmacion: '' },
  });
  const confirmar = handleSubmit(({ username, password }) => {
    setFallo(null);
    crear.mutate(
      { id: socio.id, username, password },
      {
        onSuccess: () => {
          mostrar('Cuenta creada');
          onCerrar();
        },
        onError: (error) => {
          if (error.codigo === 'DUPLICADO') {
            setError('username', { message: 'Ya existe un usuario con ese nombre de usuario' });
          } else setFallo(error);
        },
      },
    );
  });
  return (
    <ConfirmDialog
      titulo={`Cuenta de acceso de ${nombreDe(socio)}`}
      descripcion="Con esta cuenta el socio consulta el catálogo, sus préstamos y reservas."
      textoConfirmar="Crear cuenta"
      procesando={crear.isPending}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <Input
        etiqueta="Usuario"
        requerido
        autoComplete="off"
        ayuda="De 3 a 50 caracteres: letras, números, punto o guiones."
        error={errors.username?.message}
        {...register('username')}
      />
      <Input
        etiqueta="Contraseña"
        type="password"
        requerido
        autoComplete="new-password"
        ayuda="De 10 a 128 caracteres, con al menos una letra y un número."
        error={errors.password?.message}
        {...register('password')}
      />
      <Input
        etiqueta="Repetir contraseña"
        type="password"
        requerido
        autoComplete="new-password"
        error={errors.confirmacion?.message}
        {...register('confirmacion')}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
