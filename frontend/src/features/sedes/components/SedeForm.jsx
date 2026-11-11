import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Combobox,
  Input,
  WeekScheduleEditor,
  useToast,
} from '../../../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../../../utils/errores.js';
import { aplanarHorarios, agruparHorarios, validarHorarios } from '../horarios.js';
import { esquemaSede } from '../esquema.js';
import { useCrearSede, useModificarSede } from '../hooks/useSedesMutaciones.js';
import { useLocalidades } from '../hooks/useSedes.js';
import ConflictoVersionDialog from './ConflictoVersionDialog.jsx';
import DireccionDuplicadaDialog from './DireccionDuplicadaDialog.jsx';
import estilos from './Sedes.module.css';

const CAMPOS_DEL_FORMULARIO = [
  'codigo',
  'nombre',
  'calle',
  'numero',
  'localidad_id',
  'telefono',
  'email',
  'responsable',
];
// Códigos de error sin `detalles` que conviene mostrar junto al campo que los causa.
const CAMPO_DEL_ERROR = {
  SEDE_CODIGO_DUPLICADO: 'codigo',
  SEDE_NOMBRE_DUPLICADO: 'nombre',
  LOCALIDAD_INVALIDA: 'localidad_id',
};

function valoresIniciales(sede) {
  return {
    codigo: sede?.codigo ?? '',
    nombre: sede?.nombre ?? '',
    calle: sede?.direccion.calle ?? '',
    numero: sede?.direccion.numero ?? '',
    localidad_id: sede?.direccion.localidad_id,
    telefono: sede?.contacto.telefono ?? '',
    email: sede?.contacto.email ?? '',
    responsable: sede?.contacto.responsable ?? '',
  };
}

/**
 * Formulario de alta (sin `sede`) y de edición (con `sede`). En la edición envía la versión leída
 * al abrirlo: si otra persona modificó la sede, el servidor responde `CONFLICTO_DE_VERSION`.
 */
export default function SedeForm({ sede, onRecargar }) {
  const editando = Boolean(sede);
  const navegar = useNavigate();
  const queryClient = useQueryClient();
  const { mostrar } = useToast();
  const crear = useCrearSede();
  const modificar = useModificarSede(sede?.id);
  const mutacion = editando ? modificar : crear;
  const [versionLeida] = useState(sede?.version);
  const [horarios, setHorarios] = useState(() => agruparHorarios(sede?.horarios));
  const [intentado, setIntentado] = useState(false);
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [duplicada, setDuplicada] = useState(null);
  const [conflicto, setConflicto] = useState(false);
  const ultimoCuerpo = useRef(null);
  const localidades = useLocalidades();

  const {
    register,
    control,
    handleSubmit,
    setError,
    setFocus,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaSede),
    defaultValues: valoresIniciales(sede),
  });

  const opciones = (localidades.data ?? []).map((l) => ({
    id: l.id,
    texto: l.nombre,
    detalle: l.departamento,
  }));
  const localidadElegida = (localidades.data ?? []).find((l) => l.id === watch('localidad_id'));

  const problemas = validarHorarios(horarios);
  const problemasVisibles = intentado ? problemas : { ...problemas, general: undefined };
  const hayProblemasDeHorario = Object.keys(problemas).length > 0;

  function enviar(cuerpo) {
    ultimoCuerpo.current = cuerpo;
    setErrorGeneral(null);
    mutacion.mutate(cuerpo, {
      onSuccess: (guardada) => {
        mostrar('Sede guardada');
        navegar(`/sedes/${guardada.id}`);
      },
      onError: (error) => {
        if (error.codigo === 'DIRECCION_DUPLICADA') return setDuplicada(error);
        if (error.codigo === 'CONFLICTO_DE_VERSION') return setConflicto(true);
        const porCampo = erroresPorCampo(error);
        if (error.codigo in CAMPO_DEL_ERROR) {
          porCampo[CAMPO_DEL_ERROR[error.codigo]] ??= mensajeDeError(error);
        }
        const campos = CAMPOS_DEL_FORMULARIO.filter((c) => porCampo[c]);
        for (const campo of campos) setError(campo, { message: porCampo[campo] });
        if (campos.length > 0) setFocus(campos[0]);
        else setErrorGeneral(mensajeDeError(error));
        return undefined;
      },
    });
  }

  function alEnviar(datos) {
    setIntentado(true);
    if (hayProblemasDeHorario) return;
    const base = {
      nombre: datos.nombre,
      calle: datos.calle,
      numero: datos.numero,
      localidad_id: datos.localidad_id,
      telefono: datos.telefono,
      email: datos.email,
      responsable: datos.responsable,
      horarios: aplanarHorarios(horarios),
      confirmar_direccion_duplicada: false,
    };
    enviar(
      editando
        ? { ...base, codigo: sede.codigo, version: versionLeida }
        : { ...base, codigo: datos.codigo.toUpperCase() },
    );
  }

  return (
    <form
      className={estilos.formulario}
      noValidate
      onSubmit={(e) => {
        setIntentado(true);
        handleSubmit(alEnviar)(e);
      }}
    >
      {errorGeneral && <Alert tono="danger">{errorGeneral}</Alert>}

      <Card titulo="Identificación">
        <div className={estilos.grupo}>
          <Controller
            name="codigo"
            control={control}
            render={({ field }) => (
              <Input
                etiqueta="Código"
                requerido={!editando}
                disabled={editando}
                ayuda={
                  editando
                    ? 'El código no se puede cambiar'
                    : '3 a 15 caracteres: letras, números o guion bajo'
                }
                error={errors.codigo?.message}
                maxLength={15}
                {...field}
                onChange={(e) => field.onChange(e.target.value.toUpperCase())}
              />
            )}
          />
          <Input
            etiqueta="Nombre"
            requerido
            error={errors.nombre?.message}
            {...register('nombre')}
          />
        </div>
      </Card>

      <Card titulo="Domicilio">
        <div className={estilos.grupo}>
          <Input etiqueta="Calle" requerido error={errors.calle?.message} {...register('calle')} />
          <Input
            etiqueta="Número"
            requerido
            ayuda="Número de puerta (1250, 1250B) o S/N"
            error={errors.numero?.message}
            {...register('numero')}
          />
          <Controller
            name="localidad_id"
            control={control}
            render={({ field }) => (
              <Combobox
                etiqueta="Localidad"
                requerido
                opciones={opciones}
                valor={field.value ?? ''}
                onCambiar={(id) => field.onChange(id === '' ? undefined : id)}
                error={errors.localidad_id?.message}
                inputRef={field.ref}
              />
            )}
          />
          <Input
            etiqueta="Provincia"
            readOnly
            value={localidadElegida?.provincia ?? ''}
            ayuda="Se completa con la localidad"
          />
        </div>
      </Card>

      <Card titulo="Contacto">
        <div className={estilos.grupo}>
          <Input
            etiqueta="Teléfono"
            requerido
            type="tel"
            ayuda="Formato internacional, por ejemplo +54 351 422 1234"
            error={errors.telefono?.message}
            {...register('telefono')}
          />
          <Input
            etiqueta="Correo electrónico"
            requerido
            type="email"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            etiqueta="Responsable"
            requerido
            error={errors.responsable?.message}
            {...register('responsable')}
          />
        </div>
      </Card>

      <Card titulo="Horarios de atención">
        <WeekScheduleEditor
          valor={horarios}
          onCambiar={setHorarios}
          problemas={problemasVisibles}
        />
      </Card>

      <div className={estilos.barraDeAcciones}>
        <Button type="submit" cargando={mutacion.isPending}>
          Guardar sede
        </Button>
        <Button variante="secondary" to={editando ? `/sedes/${sede.id}` : '/sedes'}>
          Cancelar
        </Button>
      </div>

      {duplicada && (
        <DireccionDuplicadaDialog
          error={duplicada}
          procesando={mutacion.isPending}
          onCorregir={() => setDuplicada(null)}
          onConfirmar={() => {
            const cuerpo = { ...ultimoCuerpo.current, confirmar_direccion_duplicada: true };
            setDuplicada(null);
            enviar(cuerpo);
          }}
        />
      )}
      {conflicto && (
        <ConflictoVersionDialog
          onRecargar={async () => {
            setConflicto(false);
            await queryClient.refetchQueries({ queryKey: ['sedes', 'detalle', String(sede?.id)] });
            onRecargar?.();
          }}
        />
      )}
    </form>
  );
}
