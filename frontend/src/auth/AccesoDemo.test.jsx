import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { error, registrar, responder, sesionDe } from '../../tests/handlers.js';
import { ADMIN, pagina, sedeAdmin } from '../../tests/datos.js';
import { renderizarApp } from '../../tests/render.jsx';

const INICIO = { sedes_activas: 4, libros: 120, ejemplares: 900, destacados: [] };
const VISITANTE = { ...ADMIN, nombre: 'Visitante', solo_lectura: true };

function conAccesoDemo() {
  vi.stubEnv('VITE_DEMO_USUARIO', 'visitante');
  vi.stubEnv('VITE_DEMO_CLAVE', 'visitante1');
}

function inicioDelAdmin() {
  responder('get', '/sedes/resumen', { total: 1, activas: 1, en_baja: 0 });
  responder('get', '/sedes', pagina([sedeAdmin()]));
}

describe('AccesoDemo', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('sin las variables del deploy no aparece ni en el inicio ni en el login', async () => {
    responder('get', '/publico/inicio', INICIO);
    renderizarApp('/login');

    expect(await screen.findByRole('heading', { name: 'Ingresar' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Entrar como visitante/ })).toBeNull();
  });

  it('en el inicio público muestra el usuario y la contraseña y entra con un clic', async () => {
    conAccesoDemo();
    responder('get', '/publico/inicio', INICIO);
    const logins = registrar('post', '/auth/login', {
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      usuario: VISITANTE,
    });
    inicioDelAdmin();
    const { container } = renderizarApp('/');

    const cartel = await screen.findByRole('region', { name: '¿Querés recorrer el sistema?' });
    expect(within(cartel).getByText('visitante')).toBeInTheDocument();
    expect(within(cartel).getByText('visitante1')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(within(cartel).getByRole('button', { name: /Entrar como visitante/ }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument();
    expect(logins[0].cuerpo).toEqual({ username: 'visitante', password: 'visitante1' });
    expect(screen.getByText('Modo demostración')).toBeInTheDocument();
  });

  it('en el login avisa si el usuario de demostración no existe en el deploy', async () => {
    conAccesoDemo();
    responder('get', '/publico/inicio', INICIO);
    responder('post', '/auth/login', () =>
      error(401, 'CREDENCIALES_INVALIDAS', 'Usuario o contraseña incorrectos.'),
    );
    renderizarApp('/login');

    await userEvent.click(await screen.findByRole('button', { name: /Entrar como visitante/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos');
  });

  it('un usuario común no ve el aviso de modo demostración', async () => {
    sesionDe(ADMIN);
    inicioDelAdmin();
    renderizarApp('/', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument();
    expect(screen.queryByText('Modo demostración')).toBeNull();
  });
});
