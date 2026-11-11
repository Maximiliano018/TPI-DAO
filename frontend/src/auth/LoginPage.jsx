import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { Alert, Button, Input } from '../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../utils/errores.js';
import { MENSAJES } from '../utils/mensajes.js';
import { useSesion } from './SesionContext.jsx';
import estilos from './LoginPage.module.css';

const esquema = z.object({
  username: z.string().trim().min(1, 'Ingrese su usuario'),
  password: z.string().min(1, 'Ingrese su contraseña'),
});

export default function LoginPage() {
  const { estado, aviso, iniciar } = useSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [error, setError] = useState(null);
  const [verClave, setVerClave] = useState(false);
  const {
    register,
    handleSubmit,
    setFocus,
    setError: setErrorCampo,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(esquema), defaultValues: { username: '', password: '' } });

  useEffect(() => setFocus('username'), [setFocus]);

  if (estado === 'autenticado') return <Navigate to={ubicacion.state?.desde ?? '/'} replace />;

  async function ingresar({ username, password }) {
    setError(null);
    try {
      await iniciar(username.trim(), password);
      navegar(ubicacion.state?.desde ?? '/', { replace: true });
    } catch (fallo) {
      const campos = erroresPorCampo(fallo);
      if (fallo.estado === 422 && Object.keys(campos).length > 0) {
        Object.entries(campos).forEach(([campo, problema]) =>
          setErrorCampo(campo, { message: problema }),
        );
      } else {
        setError(mensajeDeError(fallo));
      }
    }
  }

  return (
    <main className={estilos.pagina} id="contenido">
      <form className={estilos.formulario} onSubmit={handleSubmit(ingresar)} noValidate>
        <h1 className={estilos.titulo}>{MENSAJES.sistemaCompleto}</h1>
        <p className={estilos.subtitulo}>Ingrese con su usuario y contraseña.</p>
        {aviso && <Alert tono="warning">{aviso}</Alert>}
        {error && <Alert tono="danger">{error}</Alert>}
        <Input
          etiqueta="Usuario"
          autoComplete="username"
          autoCapitalize="none"
          error={errors.username?.message}
          {...register('username')}
        />
        <Input
          etiqueta="Contraseña"
          type={verClave ? 'text' : 'password'}
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <Button variante="link" onClick={() => setVerClave((v) => !v)} aria-pressed={verClave}>
          {verClave ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        </Button>
        <Button type="submit" cargando={isSubmitting}>
          Ingresar
        </Button>
      </form>
    </main>
  );
}
