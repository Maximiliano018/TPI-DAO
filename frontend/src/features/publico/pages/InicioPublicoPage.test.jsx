import { screen, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { error, responder } from '../../../../tests/handlers.js';
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
    expect(screen.getByText('Ejemplares en la red')).toBeInTheDocument();
  });

  it('los libros que completan la lista sin préstamos no llevan puesto', async () => {
    const nuevo = { ...INICIO.destacados[1], libro_id: 3, titulo: 'Kentukis', pedidos: 0 };
    responder('get', '/publico/inicio', { ...INICIO, destacados: [INICIO.destacados[0], nuevo] });
    renderizarApp('/');

    const libros = await within(await screen.findByRole('list')).findAllByRole('listitem');
    expect(within(libros[0]).getByText('Puesto')).toBeInTheDocument();
    expect(within(libros[1]).queryByText('Puesto')).not.toBeInTheDocument();
    expect(within(libros[1]).queryByText(/préstamo/)).not.toBeInTheDocument();
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

    expect(await screen.findByText('Todavía no hay préstamos para mostrar.')).toBeInTheDocument();
  });

  it('si el backend no responde lo avisa, en lugar de decir que no hay pedidos', async () => {
    responder('get', '/publico/inicio', () => error(500, 'ERROR_INTERNO', 'Falla'));
    renderizarApp('/');

    expect(
      await screen.findByText(/No se pudieron cargar los libros más pedidos/),
    ).toBeInTheDocument();
    expect(screen.queryByText('Todavía no hay préstamos para mostrar.')).not.toBeInTheDocument();
  });

  it('no tiene violaciones de accesibilidad', async () => {
    responder('get', '/publico/inicio', INICIO);
    const { container } = renderizarApp('/');

    await screen.findByRole('heading', { name: 'Rayuela' });
    expect(await axe(container)).toHaveNoViolations();
  });
});
