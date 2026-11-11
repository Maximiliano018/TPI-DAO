import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { error, responder, sesionDe } from '../../tests/handlers.js';
import { ADMIN, sedeAdmin, pagina } from '../../tests/datos.js';
import { renderizarApp } from '../../tests/render.jsx';

describe('App', () => {
  it('sin sesión lleva al login', async () => {
    renderizarApp('/');

    expect(
      await screen.findByRole('heading', { name: /préstamos interbibliotecarios/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Usuario')).toBeInTheDocument();
  });

  it('con sesión guardada muestra el inicio dentro del layout', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 1, activas: 1, en_baja: 0 });
    responder('get', '/sedes', pagina([sedeAdmin()]));
    renderizarApp('/', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument();
  });

  it('una ruta desconocida muestra «no encontrada» sin perder el layout', async () => {
    sesionDe(ADMIN);
    renderizarApp('/no-existe', { conSesion: true });

    expect(await screen.findByText('La pantalla que busca no existe')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument();
  });

  it('un token vencido al restaurar la sesión lleva al login', async () => {
    responder('get', '/auth/me', () => error(401, 'TOKEN_INVALIDO', 'Su sesión venció.'));
    renderizarApp('/', { conSesion: true });

    expect(await screen.findByLabelText('Usuario')).toBeInTheDocument();
    expect(sessionStorage.getItem('tpi.token')).toBeNull();
  });

  it('/version es pública y muestra el estado del backend', async () => {
    const { http, HttpResponse } = await import('msw');
    const { servidor } = await import('../../tests/servidor.js');
    servidor.use(
      http.get('http://localhost/api/version', () =>
        HttpResponse.json({ servicio: 'backend', estado: 'ok', version: '9.9.9' }),
      ),
    );
    renderizarApp('/version');

    expect(await screen.findByText('9.9.9')).toBeInTheDocument();
    expect(screen.getAllByText('En línea')).toHaveLength(2);
  });
});
