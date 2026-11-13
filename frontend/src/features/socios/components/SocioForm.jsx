import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
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
import { ROLES } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import { TIPOS_DE_DOCUMENTO, esquemaSocio } from '../esquema.js';
import { useCrearSocio, useModificarSocio } from '../hooks/useSocios.js';

const CAMPOS = [
  'tipo_documento',
  'nro_documento',
  'nombre',
  'apellido',
  'fecha_nacimiento',
  'email',
  'telefono',
  'domicilio',
  'sede_alta_id',
];

const comoNumero = (valor) => (valor === '' ? undefined : Number(valor));
const vacioANulo = (valor) => (valor === '' ? null : valor);

/**
 * Alta (sin `socio`) y edición (con `socio`) de un socio. El administrador elige la sede de alta;
 * el bibliotecario registra en la suya. Si el backend detecta un duplicado, se muestra el socio
 * existente (con su ficha para reactivarlo si está en baja) o se pide confirmar que es otra persona.
 */
export default function SocioForm({ socio }) {
  const { usuario } = useSesion();
  const eligeSede = !socio && usuario.rol === ROLES.ADMIN;
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 });
  if (eligeSede && sedes.isPending) return <Skeleton alto={200} />;
  if (eligeSede && sedes.error)
    return <ErrorState error={sedes.error} onReintentar={sedes.refetch} />;
  return (
    <Formulario
      socio={socio}
      sedesActivas={eligeSede ? sedes.data.items : null}
      sedePropia={usuario.sede}
    />
  );
}

function Formulario({ socio, sedesActivas, sedePropia }) {
  const editando = Boolean(socio);
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const crear = useCrearSocio();
  const modificar = useModificarSocio(socio?.id);
  const mutacion = editando ? modificar : crear;
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [existente, setExistente] = useState(null);
  const [parecidos, setParecidos] = useState(null);

  const {
    register,
    handleSubmit,
    setError,
    setFocus,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaSocio),
    defaultValues: {
      tipo_documento: socio?.tipo_documento ?? 'DNI',
      nro_documento: socio?.nro_documento ?? '',
      nombre: socio?.nombre ?? '',
      apellido: socio?.apellido ?? '',
      fecha_nacimiento: socio?.fecha_nacimiento ?? '',
      email: socio?.email ?? '',
      telefono: socio?.telefono ?? '',
      domicilio: socio?.domicilio ?? '',
      sede_alta_id: undefined,
    },
  });

  function enviar(datos, confirmar = false) {
    setErrorGeneral(null);
    setExistente(null);
    setParecidos(null);
    const cuerpo = {
      tipo_documento: datos.tipo_documento,
      nro_documento: datos.nro_documento,
      nombre: datos.nombre,
      apellido: datos.apellido,
      fecha_nacimiento: vacioANulo(datos.fecha_nacimiento),
      email: vacioANulo(datos.email),
      telefono: vacioANulo(datos.telefono),
      domicilio: vacioANulo(datos.domicilio),
    };
    if (!editando) {
      cuerpo.sede_alta_id = sedesActivas ? (datos.sede_alta_id ?? null) : null;
      cuerpo.confirmar_posible_duplicado = confirmar;
    }
    mutacion.mutate(cuerpo, {
      onSuccess: (guardado) => {
        mostrar(editando ? 'Socio guardado' : `Socio ${guardado.numero_socio} registrado`);
        navegar(`/socios/${guardado.id}`);
      },
      onError: (error) => {
        if (error.codigo === 'DUPLICADO') {
          setExistente(error.detalles[0] ?? null);
          setErrorGeneral(error.mensaje);
          return;
        }
        if (error.codigo === 'POSIBLE_DUPLICADO') {
          setParecidos({ socios: error.detalles, datos });
          return;
        }
        const porCampo = erroresPorCampo(error);
        const campos = CAMPOS.filter((c) => porCampo[c]);
        for (const c of campos) setError(c, { message: porCampo[c] });
        if (campos.length > 0) setFocus(campos[0]);
        else setErrorGeneral(mensajeDeError(error));
      },
    });
  }

  return (
    <form className={estilos.formulario} noValidate onSubmit={handleSubmit((d) => enviar(d))}>
      {errorGeneral && (
        <Alert tono="danger">
          {errorGeneral}
          {existente?.socio_id && (
            <>
              {' '}
              <Link to={`/socios/${existente.socio_id}`}>
                Ver la ficha del socio {existente.numero_socio}
              </Link>
            </>
          )}
        </Alert>
      )}
      {parecidos && (
        <Alert tono="warning">
          <p style={{ margin: 0 }}>
            Ya hay socios con el mismo nombre y fecha de nacimiento. Revise que no sea la misma
            persona:
          </p>
          <ul>
            {parecidos.socios.map((p) => (
              <li key={p.socio_id}>
                <Link to={`/socios/${p.socio_id}`}>
                  {p.numero_socio} · {p.nombre}
                </Link>
              </li>
            ))}
          </ul>
          <Button
            variante="secondary"
            tamano="sm"
            cargando={mutacion.isPending}
            onClick={() => enviar(parecidos.datos, true)}
          >
            Es otra persona: registrar igual
          </Button>
        </Alert>
      )}

      <Card titulo="Documento">
        <div className={estilos.grupo}>
          <Select
            etiqueta="Tipo de documento"
            requerido
            error={errors.tipo_documento?.message}
            {...register('tipo_documento')}
          >
            {TIPOS_DE_DOCUMENTO.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </Select>
          <Input
            etiqueta="Número de documento"
            requerido
            autoComplete="off"
            ayuda="Sin puntos o con puntos: se guarda solo el número."
            error={errors.nro_documento?.message}
            {...register('nro_documento')}
          />
        </div>
      </Card>

      <Card titulo="Datos personales">
        <div className={estilos.grupo}>
          <Input
            etiqueta="Nombre"
            requerido
            autoComplete="off"
            error={errors.nombre?.message}
            {...register('nombre')}
          />
          <Input
            etiqueta="Apellido"
            requerido
            autoComplete="off"
            error={errors.apellido?.message}
            {...register('apellido')}
          />
          <Input
            etiqueta="Fecha de nacimiento"
            type="date"
            ayuda="Ayuda a detectar socios duplicados."
            error={errors.fecha_nacimiento?.message}
            {...register('fecha_nacimiento')}
          />
        </div>
      </Card>

      <Card titulo="Contacto">
        <div className={estilos.grupo}>
          <Input
            etiqueta="Correo electrónico"
            type="email"
            autoComplete="off"
            ayuda="Indique al menos un correo o un teléfono."
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            etiqueta="Teléfono"
            type="tel"
            autoComplete="off"
            ayuda="Formato internacional, por ejemplo +543515000000."
            error={errors.telefono?.message}
            {...register('telefono')}
          />
          <Input
            etiqueta="Domicilio"
            autoComplete="off"
            error={errors.domicilio?.message}
            {...register('domicilio')}
          />
        </div>
      </Card>

      {!editando && (
        <Card titulo="Sede de alta">
          {sedesActivas ? (
            <div className={estilos.grupo}>
              <Select
                etiqueta="Sede"
                requerido
                ayuda="Solo se ofrecen sedes activas. El socio puede operar en toda la red."
                error={errors.sede_alta_id?.message}
                {...register('sede_alta_id', { setValueAs: comoNumero })}
              >
                <option value="">Elija una sede</option>
                {sedesActivas.map((sede) => (
                  <option key={sede.id} value={sede.id}>
                    {sede.nombre}
                  </option>
                ))}
              </Select>
            </div>
          ) : (
            <p style={{ margin: 0 }}>
              Se registra en su sede ({sedePropia?.nombre}). El socio puede operar en toda la red.
            </p>
          )}
        </Card>
      )}

      <div className={estilos.barraDeAcciones}>
        <Button type="submit" cargando={mutacion.isPending}>
          {editando ? 'Guardar cambios' : 'Registrar socio'}
        </Button>
        <Button variante="secondary" to={editando ? `/socios/${socio.id}` : '/socios'}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
