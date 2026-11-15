import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { obtenerInicioPublico } from '../api/publico.js';
import { Alert, Button, Input, InputClave, Logo } from '../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../utils/errores.js';
import { MENSAJES } from '../utils/mensajes.js';
import { useSesion } from './SesionContext.jsx';
import estilos from './LoginPage.module.css';

const esquema = z.object({
  username: z.string().trim().min(1, 'Ingrese su usuario'),
  password: z.string().min(1, 'Ingrese su contraseña'),
});

const LOMOS = ['burdeos', 'bosque', 'marino', 'ocre', 'ciruela', 'petroleo'];

/** Ingreso: a la izquierda la red (lema, cifras y un estante); a la derecha, el formulario. */
export default function LoginPage() {
  const { estado, aviso, iniciar, limpiarAviso } = useSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [error, setError] = useState(null);
  const [mayusculas, setMayusculas] = useState(false);
  const red = useQuery({
    queryKey: ['publico', 'inicio'],
    queryFn: () => obtenerInicioPublico(12),
    staleTime: 60_000,
    retry: false,
  });
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

  // Avisa si el Bloq Mayús está activado mientras se escribe la contraseña.
  const revisarMayusculas = (evento) => setMayusculas(evento.getModifierState?.('CapsLock'));

  return (
    <main className={estilos.pagina} id="contenido">
      <section className={estilos.red} aria-label="La red de bibliotecas">
        <Link to="/" className={estilos.marca} onClick={limpiarAviso}>
          <Logo tamano={28} />
          {MENSAJES.sistema}
        </Link>
        <div>
          <p className={estilos.volanta}>Red de bibliotecas públicas</p>
          <p className={estilos.lema}>
            Todos los libros de la red, <em>a una sede</em> de distancia.
          </p>
          <p className={estilos.cita}>
            “Pedí un libro en cualquier sede y retiralo en la que te quede más cerca.”
          </p>
          {red.data && (
            <dl className={estilos.cifras}>
              <div>
                <dt>sedes</dt>
                <dd>{red.data.sedes_activas}</dd>
              </div>
              <div>
                <dt>ejemplares</dt>
                <dd>{red.data.ejemplares.toLocaleString('es-AR')}</dd>
              </div>
            </dl>
          )}
        </div>
        <div className={estilos.estante} aria-hidden="true">
          {Array.from({ length: 16 }, (_, i) => (
            <span
              key={i}
              className={estilos.lomo}
              style={{
                '--c': `var(--lomo-${LOMOS[(i * 5) % LOMOS.length]})`,
                height: `${78 + ((i * 29) % 52)}px`,
                width: `${22 + ((i * 11) % 16)}px`,
              }}
            />
          ))}
        </div>
      </section>

      <section className={estilos.acceso}>
        <form className={estilos.formulario} onSubmit={handleSubmit(ingresar)} noValidate>
          <h1 className={estilos.titulo}>Ingresar</h1>
          <p className={estilos.subtitulo}>Con su usuario de la red de bibliotecas.</p>
          {aviso && <Alert tono="warning">{aviso}</Alert>}
          {error && <Alert tono="danger">{error}</Alert>}
          <Input
            etiqueta="Usuario"
            autoComplete="username"
            autoCapitalize="none"
            error={errors.username?.message}
            {...register('username')}
          />
          <InputClave
            etiqueta="Contraseña"
            autoComplete="current-password"
            error={errors.password?.message}
            onKeyUp={revisarMayusculas}
            onKeyDown={revisarMayusculas}
            {...register('password')}
          />
          {mayusculas && (
            <p className={estilos.mayusculas} role="status">
              ⚠ Bloq Mayús está activado
            </p>
          )}
          <Button type="submit" cargando={isSubmitting}>
            Ingresar <span aria-hidden="true">→</span>
          </Button>
          <p className={estilos.ayuda}>¿Olvidó su contraseña? Pídala en el mostrador de su sede.</p>
        </form>
        <footer className={estilos.pie}>
          <span>{MENSAJES.sistemaCompleto} · UTN FRC 2026</span>
          <Link to="/" onClick={limpiarAviso}>
            Volver al inicio
          </Link>
        </footer>
      </section>
    </main>
  );
}
