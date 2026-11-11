import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { error, responder } from '../../tests/handlers.js';
import { ADMIN, pagina, sedeAdmin } from '../../tests/datos.js';
import { renderizarApp } from '../../tests/render.jsx';

async function escribir(usuario, clave) {
  const user = userEvent.setup();
  if (usuario) await user.type(screen.getByLabelText('Usuario'), usuario);
  if (clave) await user.type(screen.getByLabelText('Contraseña'), clave);
  return user;
}

describe('LoginPage', () => {
  it('enfoca el usuario al abrir y no tiene violaciones de accesibilidad', async () => {
    const { container } = renderizarApp('/login');

    expect(await screen.findByLabelText('Usuario')).toHaveFocus();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('con credenciales correctas guarda el token y lleva al inicio', async () => {
    responder('post', '/auth/login', {
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      usuario: ADMIN,
    });
    responder('get', '/sedes/resumen', { total: 0, activas: 0, en_baja: 0 });
    responder('get', '/sedes', pagina([sedeAdmin()]));
    renderizarApp('/login');

    const user = await escribir('ana.admin', 'Clave-1234567');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument();
    expect(sessionStorage.getItem('tpi.token')).toBe('tok');
  });

  it('Enter envía el formulario', async () => {
    responder('post', '/auth/login', { access_token: 'tok', usuario: ADMIN });
    responder('get', '/sedes/resumen', { total: 0, activas: 0, en_baja: 0 });
    responder('get', '/sedes', pagina([]));
    renderizarApp('/login');

    const user = await escribir('ana.admin', 'Clave-1234567');
    await user.keyboard('{Enter}');

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument();
  });

  it('credenciales inválidas muestran un aviso general que no revela cuál dato falló', async () => {
    responder('post', '/auth/login', () =>
      error(401, 'CREDENCIALES_INVALIDAS', 'Usuario o contraseña incorrectos.'),
    );
    renderizarApp('/login');

    const user = await escribir('ana.admin', 'mala-clave');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos');
    expect(sessionStorage.getItem('tpi.token')).toBeNull();
  });

  it('un error de red pide reintentar', async () => {
    const { servidor } = await import('../../tests/servidor.js');
    const { http, HttpResponse } = await import('msw');
    servidor.use(http.post('http://localhost/api/v1/auth/login', () => HttpResponse.error()));
    renderizarApp('/login');

    const user = await escribir('ana.admin', 'x');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar. Reintente.');
  });

  it('valida los campos obligatorios antes de enviar', async () => {
    renderizarApp('/login');
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: 'Ingresar' }));

    expect(await screen.findByText('Ingrese su usuario')).toBeInTheDocument();
    expect(screen.getByText('Ingrese su contraseña')).toBeInTheDocument();
  });

  it('un 422 del servidor se muestra junto al campo', async () => {
    responder('post', '/auth/login', () =>
      error(422, 'VALIDACION', 'Datos inválidos', [
        { campo: 'username', problema: 'Usuario inválido' },
      ]),
    );
    renderizarApp('/login');

    const user = await escribir('x', 'y');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(await screen.findByText('Usuario inválido')).toBeInTheDocument();
  });

  it('permite mostrar y ocultar la contraseña', async () => {
    renderizarApp('/login');
    const user = userEvent.setup();

    const campo = await screen.findByLabelText('Contraseña');
    expect(campo).toHaveAttribute('type', 'password');
    await user.click(screen.getByRole('button', { name: 'Mostrar contraseña' }));
    expect(campo).toHaveAttribute('type', 'text');
    await user.click(screen.getByRole('button', { name: 'Ocultar contraseña' }));
    expect(campo).toHaveAttribute('type', 'password');
  });

  it('tras ingresar vuelve a la ruta de origen', async () => {
    responder('post', '/auth/login', { access_token: 'tok', usuario: ADMIN });
    renderizarApp('/ruta-protegida-que-no-existe');

    const user = await escribir('ana.admin', 'Clave-1234567');
    await user.click(await screen.findByRole('button', { name: 'Ingresar' }));

    await waitFor(() =>
      expect(screen.getByText('La pantalla que busca no existe')).toBeInTheDocument(),
    );
  });
});
