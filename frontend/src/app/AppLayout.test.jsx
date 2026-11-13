import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { responder, sesionDe } from '../../tests/handlers.js';
import { ADMIN, BIBLIOTECARIO, SOCIO, pagina, sedeBasica, sedePublica } from '../../tests/datos.js';
import { renderizarApp } from '../../tests/render.jsx';

function menu() {
  return screen.getByRole('navigation', { name: 'Navegación principal' });
}

describe('AppLayout', () => {
  it('el administrador ve todos los módulos del personal; la sede es «Toda la red»', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 0, activas: 0, en_baja: 0 });
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'Inicio' });
    expect(
      within(menu())
        .getAllByRole('link')
        .map((l) => l.textContent),
    ).toEqual([
      'Inicio',
      'Sedes',
      'Catálogo',
      'Ejemplares',
      'Préstamos',
      'Reservas',
      'Remitos',
      'Multas',
      'Socios',
      'Reportes',
      'Usuarios',
      'Parámetros',
    ]);
    expect(screen.getByTestId('sede-del-usuario')).toHaveTextContent('Toda la red');
  });

  it('el bibliotecario no ve Usuarios y su sede aparece en la barra', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/sedes/1', sedeBasica());
    responder('get', '/sedes', pagina([sedeBasica()]));
    renderizarApp('/', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'Inicio' });
    expect(within(menu()).queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument();
    expect(screen.getByTestId('sede-del-usuario')).toHaveTextContent('Sede Central');
  });

  it('el ítem de la ruta activa se marca con aria-current', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([sedePublica()]));
    renderizarApp('/', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'Inicio' });
    expect(within(menu()).getByRole('link', { name: 'Inicio' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(menu()).getByRole('link', { name: 'Sedes' })).not.toHaveAttribute('aria-current');
  });

  it('el menú de usuario muestra nombre y rol y cierra la sesión', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 0, activas: 0, en_baja: 0 });
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /Ana Admin/ }));
    expect(screen.getByText('Administrador')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));

    expect(await screen.findByLabelText('Usuario')).toBeInTheDocument();
    expect(sessionStorage.getItem('tpi.token')).toBeNull();
  });

  it('el botón de menú abre y cierra el panel; Escape lo cierra', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 0, activas: 0, en_baja: 0 });
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });
    const user = userEvent.setup();

    const boton = await screen.findByRole('button', { name: 'Menú de navegación' });
    expect(boton).toHaveAttribute('aria-expanded', 'false');
    await user.click(boton);
    expect(boton).toHaveAttribute('aria-expanded', 'true');
    expect(within(menu()).getByRole('link', { name: 'Inicio' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(boton).toHaveAttribute('aria-expanded', 'false');
  });

  it('tiene un salto al contenido y una región main', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'Inicio' });
    expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveAttribute(
      'href',
      '#contenido',
    );
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('un 401 en cualquier pantalla vuelve al login con el aviso de sesión vencida', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', () => {
      return new Response(
        JSON.stringify({ error: { codigo: 'TOKEN_INVALIDO', mensaje: 'Vencida', detalles: [] } }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    });
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });

    expect(await screen.findByText('Su sesión venció. Ingrese de nuevo.')).toBeInTheDocument();
    expect(screen.getByLabelText('Usuario')).toBeInTheDocument();
  });

  it('no tiene violaciones de accesibilidad', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 1, activas: 1, en_baja: 0 });
    responder('get', '/sedes', pagina([sedeBasica()]));
    const { container } = renderizarApp('/', { conSesion: true });

    await screen.findByText('Sedes de la red');
    expect(await axe(container)).toHaveNoViolations();
  });
});
