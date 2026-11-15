import { screen, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { responder } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const INICIO = {
  sedes_activas: 5,
  libros: 124,
  ejemplares: 1350,
  destacados: [
    {
      libro_id: 1,
      titulo: 'Rayuela',
      autores: ['Julio Cortázar'],
      portada_url: '/portadas/rayuela.jpg',
      pedidos: 14,
    },
    {
      libro_id: 2,
      titulo: 'El Aleph',
      autores: ['Jorge Luis Borges'],
      portada_url: null,
      pedidos: 1,
    },
  ],
};

describe('InicioPublicoPage', () => {
  it('muestra la red y los libros más pedidos con su portada, en orden', async () => {
    responder('get', '/publico/inicio', INICIO);
    renderizarApp('/');

    const lista = await screen.findByRole('list');
    const libros = await within(lista).findAllByRole('listitem');
    expect(libros).toHaveLength(2);
    expect(within(libros[0]).getByRole('heading', { name: 'Rayuela' })).toBeInTheDocument();
    expect(within(libros[0]).getByText('Puesto')).toBeInTheDocument();
    expect(within(libros[0]).getByText('14 préstamos')).toBeInTheDocument();
    expect(within(libros[0]).getByRole('img', { name: 'Portada de Rayuela' })).toHaveAttribute(
      'src',
      '/portadas/rayuela.jpg',
    );
    // Sin imagen, la portada se dibuja con el título y el autor.
    expect(within(libros[1]).getByRole('img', { name: 'Portada de El Aleph' })).toBeInTheDocument();
    expect(within(libros[1]).getByText('1 préstamo')).toBeInTheDocument();
    expect(screen.getByText('1.350')).toBeInTheDocument();
  });

  it('ofrece ingresar al sistema arriba a la derecha y desde la portada', async () => {
    responder('get', '/publico/inicio', INICIO);
    renderizarApp('/');

    expect(await screen.findByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/login');
    expect(screen.getByRole('link', { name: 'Ingresar al sistema' })).toHaveAttribute(
      'href',
      '/login',
    );
  });

  it('sin libros pedidos todavía lo dice', async () => {
    renderizarApp('/');

    expect(
      await screen.findByText('Pronto vas a ver acá los libros más pedidos.'),
    ).toBeInTheDocument();
  });

  it('no tiene violaciones de accesibilidad', async () => {
    responder('get', '/publico/inicio', INICIO);
    const { container } = renderizarApp('/');

    await screen.findByRole('heading', { name: 'Rayuela' });
    expect(await axe(container)).toHaveNoViolations();
  });
});
