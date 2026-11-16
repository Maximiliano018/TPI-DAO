import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { obtenerInicioPublico } from '../api/publico.js';
import { Alert, Button, Estante, Icono, Input, InputClave, Logo } from '../components/index.js';
import { erroresPorCampo, mensajeDeError } from '../utils/errores.js';
import { MENSAJES } from '../utils/mensajes.js';
import { useSesion } from './SesionContext.jsx';
import estilos from './LoginPage.module.css';

const esquema = z.object({
  username: z.string().trim().min(1, 'Ingrese su usuario'),
  password: z.string().min(1, 'Ingrese su contraseña'),
});

// Lomos del estante mientras no llegan los más pedidos.
const DE_RELLENO = ['Rayuela', 'Ficciones', 'El túnel', 'Facundo', 'Martín Fierro', 'El Aleph'];

/** Ingreso: a la izquierda la red (lema, cifras y el estante); a la derecha, la tarjeta de ingreso. */
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

  const titulos = red.data?.destacados?.length
    ? red.data.destacados.map((d) => d.titulo)
    : DE_RELLENO;
  const cantidad = (n) => n.toLocaleString('es-AR');

  return (
    <div className={estilos.pagina}>
      <header className={estilos.barra}>
        <Link to="/" className={estilos.marca} onClick={limpiarAviso}>
          <Logo tamano={30} />
          <span className={estilos.sistema}>Red de Bibliotecas Públicas</span>
        </Link>
        <Link to="/" className={estilos.volver} onClick={limpiarAviso}>
          <Icono nombre="volver" />
          Volver al inicio
        </Link>
      </header>

      <main className={estilos.cuerpo} id="contenido">
        <section className={estilos.presentacion} aria-label="La red de bibliotecas">
          <p className={estilos.volanta}>Red de bibliotecas públicas · Córdoba</p>
          <p className={estilos.lema}>
            <span>Pedilo acá.</span> <span className={estilos.acento}>Retiralo allá.</span>
          </p>
          <p className={estilos.bajada}>
            Pedí un libro en cualquier sede y retiralo en la que te quede más cerca.
          </p>
          {red.data && (
            <dl className={estilos.cifras}>
              <div>
                <dt>Sedes</dt>
                <dd>{red.data.sedes_activas}</dd>
              </div>
              <div>
                <dt>Títulos</dt>
                <dd>{cantidad(red.data.libros)}</dd>
              </div>
              <div>
                <dt>Ejemplares</dt>
                <dd>{cantidad(red.data.ejemplares)}</dd>
              </div>
            </dl>
          )}
          <div className={estilos.estante}>
            <Estante titulos={titulos} />
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
            <Button type="submit" cargando={isSubmitting} className={estilos.enviar}>
              Ingresar <span aria-hidden="true">→</span>
            </Button>
            <p className={estilos.ayuda}>
              ¿Olvidó su contraseña? Pídala en el mostrador de su sede.
            </p>
          </form>
        </section>
      </main>

      <footer className={estilos.pie}>{MENSAJES.sistemaCompleto} · UTN FRC 2026</footer>
    </div>
  );
}
