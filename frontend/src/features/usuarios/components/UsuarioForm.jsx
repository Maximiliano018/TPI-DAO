import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  ErrorState,
  Input,
  Select,
  Skeleton,
  useToast,
} from '../../../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../../../utils/errores.js';
import { NOMBRE_DE_ROL } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import { esquemaCrearUsuario, esquemaEditarUsuario } from '../esquema.js';
import { useCrearUsuario, useModificarUsuario, useSedesParaElegir } from '../hooks/useUsuarios.js';

const CAMPOS = ['username', 'nombre', 'password', 'rol', 'sede_id'];
// Códigos sin `detalles` que conviene mostrar junto al campo que los causa. Para la sede se usa el
// mensaje del servidor, que ya indica qué hacer («Elija una sede activa»).
const CAMPO_DEL_ERROR = {
  DUPLICADO: ['username', null],
  SEDE_EN_BAJA: ['sede_id', 'servidor'],
  SEDE_NO_ENCONTRADA: ['sede_id', 'servidor'],
};

const comoNumero = (valor) => (valor === '' ? undefined : Number(valor));

/**
 * Alta (sin `usuario`) y edición (con `usuario`) del personal. En la edición el usuario y el rol
 * se muestran bloqueados; solo cambian el nombre y, para un bibliotecario, la sede.
 *
 * Las sedes se cargan antes de mostrar el formulario: un `<select>` nativo no puede reflejar un
 * valor precargado si todavía no existen sus opciones.
 */
export default function UsuarioForm({ usuario }) {
  const sedes = useSedesParaElegir({ soloActivas: true });
  if (sedes.isPending) return <Skeleton alto={200} />;
  if (sedes.error) return <ErrorState error={sedes.error} onReintentar={sedes.refetch} />;
  return <Formulario usuario={usuario} sedesActivas={sedes.data.items} />;
}

function Formulario({ usuario, sedesActivas }) {
  const editando = Boolean(usuario);
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const crear = useCrearUsuario();
  const modificar = useModificarUsuario(usuario?.id);
  const mutacion = editando ? modificar : crear;
  const [errorGeneral, setErrorGeneral] = useState(null);

  // Si su sede actual está en baja no figura entre las activas: debe elegir otra.
  const sedeEnBaja =
    Boolean(usuario?.sede_id) && !sedesActivas.some((x) => x.id === usuario.sede_id);

  const {
    register,
    handleSubmit,
    setError,
    setFocus,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(editando ? esquemaEditarUsuario : esquemaCrearUsuario),
    defaultValues: editando
      ? {
          nombre: usuario.nombre,
          rol: usuario.rol,
          sede_id: sedeEnBaja ? undefined : (usuario.sede_id ?? undefined),
        }
      : { username: '', nombre: '', password: '', confirmacion: '', rol: '', sede_id: undefined },
  });
  const esBibliotecario = watch('rol') === 'BIBLIOTECARIO';

  function enviar(datos) {
    setErrorGeneral(null);
    const sedeId = esBibliotecario ? (datos.sede_id ?? null) : null;
    const cuerpo = editando
      ? { nombre: datos.nombre, sede_id: sedeId }
      : {
          username: datos.username,
          password: datos.password,
          nombre: datos.nombre,
          rol: datos.rol,
          sede_id: sedeId,
        };
    mutacion.mutate(cuerpo, {
      onSuccess: () => {
        mostrar(editando ? 'Usuario guardado' : 'Usuario creado');
        navegar('/usuarios');
      },
      onError: (error) => {
        const porCampo = erroresPorCampo(error);
        const [campo, texto] = CAMPO_DEL_ERROR[error.codigo] ?? [];
        if (campo) {
          porCampo[campo] ??= texto === 'servidor' ? error.mensaje : mensajeDeError(error);
        }
        const campos = CAMPOS.filter((c) => porCampo[c]);
        for (const c of campos) setError(c, { message: porCampo[c] });
        if (campos.length > 0) setFocus(campos[0]);
        else setErrorGeneral(mensajeDeError(error));
      },
    });
  }

  return (
    <form className={estilos.formulario} noValidate onSubmit={handleSubmit(enviar)}>
      {errorGeneral && <Alert tono="danger">{errorGeneral}</Alert>}
      {editando && sedeEnBaja && esBibliotecario && (
        <Alert tono="warning">
          Su sede actual ({usuario.sede.nombre}) está dada de baja. Elija una sede activa.
        </Alert>
      )}
      {editando && !usuario.activo && (
        <Alert tono="info">
          El usuario está dado de baja. Puede reasignarlo a una sede activa y luego reactivarlo.
        </Alert>
      )}

      <Card titulo="Datos del usuario">
        <div className={estilos.grupo}>
          {editando ? (
            <>
              <Input etiqueta="Usuario" value={usuario.username} disabled readOnly />
              <Input etiqueta="Rol" value={NOMBRE_DE_ROL[usuario.rol]} disabled readOnly />
            </>
          ) : (
            <>
              <Input
                etiqueta="Usuario"
                requerido
                autoComplete="off"
                ayuda="De 3 a 50 caracteres: letras, números, punto o guiones. No se puede cambiar después."
                error={errors.username?.message}
                {...register('username')}
              />
              <Select etiqueta="Rol" requerido error={errors.rol?.message} {...register('rol')}>
                <option value="">Elija un rol</option>
                <option value="ADMIN">{NOMBRE_DE_ROL.ADMIN}</option>
                <option value="BIBLIOTECARIO">{NOMBRE_DE_ROL.BIBLIOTECARIO}</option>
              </Select>
            </>
          )}
          <Input
            etiqueta="Nombre"
            requerido
            autoComplete="off"
            error={errors.nombre?.message}
            {...register('nombre')}
          />
          {esBibliotecario && (
            <Select
              etiqueta="Sede"
              requerido
              ayuda={
                editando
                  ? 'El cambio rige desde la siguiente solicitud del usuario. Solo se ofrecen sedes activas.'
                  : 'Solo se ofrecen sedes activas.'
              }
              error={errors.sede_id?.message}
              {...register('sede_id', { setValueAs: comoNumero })}
            >
              <option value="">Elija una sede</option>
              {sedesActivas.map((sede) => (
                <option key={sede.id} value={sede.id}>
                  {sede.nombre}
                </option>
              ))}
            </Select>
          )}
        </div>
      </Card>

      {!editando && (
        <Card titulo="Contraseña inicial">
          <div className={estilos.grupo}>
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
          </div>
        </Card>
      )}

      <div className={estilos.barraDeAcciones}>
        <Button type="submit" cargando={mutacion.isPending}>
          {editando ? 'Guardar cambios' : 'Crear usuario'}
        </Button>
        <Button variante="secondary" to="/usuarios">
          Cancelar
        </Button>
      </div>
    </form>
  );
}
