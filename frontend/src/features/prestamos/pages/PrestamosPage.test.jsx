import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  BIBLIOTECARIO,
  SOCIO,
  ejemplar,
  libro,
  pagina,
  prestamo,
  socio,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

describe('Préstamos', () => {
  it('CA-ACC-04: el socio ve «Mis préstamos» sin datos de otros socios', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    responder(
      'get',
      '/prestamos',
      pagina([prestamo({ estado: 'ACTIVO', fecha_vencimiento: '2026-11-24' })]),
    );
    const user = userEvent.setup();
    const { container } = renderizarApp('/', { conSesion: true });

    await user.click(await screen.findByRole('link', { name: 'Mis préstamos' }));
    const tabla = await screen.findByRole('table', { name: 'Préstamos' });
    const encabezados = within(tabla)
      .getAllByRole('columnheader')
      .map((c) => c.textContent);
    expect(encabezados).not.toContain('Socio');
    expect(within(tabla).getByText('24/11/2026')).toBeVisible();
    expect(within(tabla).getByText('Activo')).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Nuevo préstamo' })).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('el bibliotecario entrega un préstamo local solicitado', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/prestamos/118', prestamo());
    const llamadas = registrar('post', '/prestamos/118/entregar', prestamo({ estado: 'ACTIVO' }));
    const user = userEvent.setup();
    renderizarApp('/prestamos/118', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Entregar al socio' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Entregar' }));

    expect(await screen.findByText('Préstamo entregado')).toBeVisible();
    expect(llamadas).toHaveLength(1);
    expect(screen.queryByRole('button', { name: 'Renovar' })).not.toBeInTheDocument();
  });

  it('CA-PRE-11: un préstamo entre sedes muestra su remito y no se entrega antes de llegar', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/prestamos/118',
      prestamo({
        tipo: 'INTERBIBLIOTECARIO',
        estado: 'EN_ENVIO',
        sede_origen_id: 2,
        sede_origen: 'Sede Norte',
        remitos: [
          {
            id: 51,
            numero: 'R-2026-000051',
            motivo: 'ENVIO',
            estado: 'EN_TRANSITO',
            fecha_despacho: '2026-11-11T10:00:00Z',
            fecha_recepcion: null,
          },
        ],
      }),
    );
    responder('post', '/prestamos/118/entregar', () =>
      error(409, 'EJEMPLAR_NO_RECIBIDO', 'El ejemplar todavía no llegó a la sede destino.'),
    );
    const user = userEvent.setup();
    renderizarApp('/prestamos/118', { conSesion: true });

    expect(await screen.findByRole('link', { name: 'R-2026-000051' })).toHaveAttribute(
      'href',
      '/remitos/51',
    );
    expect(screen.getByText('En tránsito')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Entregar al socio' }));
    const dialogo = screen.getByRole('dialog');
    await user.click(within(dialogo).getByRole('button', { name: 'Entregar' }));
    expect(await within(dialogo).findByText(/todavía no llegó/)).toBeVisible();
  });

  it('registrar un préstamo: socio, libro buscado en el servidor y ejemplar de otra sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/socios', pagina([socio()]));
    // El libro se busca en todo el catálogo: sin texto no hay resultados (antes solo 100 libros).
    const busquedas = registrar('get', '/libros', ({ url }) =>
      pagina(url.searchParams.get('q') === 'Rayu' ? [libro()] : []),
    );
    responder(
      'get',
      '/ejemplares',
      pagina([
        ejemplar({
          id: 305,
          codigo_inventario: 'NOR-1',
          sede_propietaria_id: 2,
          sede_propietaria: 'Sede Norte',
        }),
      ]),
    );
    const llamadas = registrar('post', '/prestamos', prestamo({ id: 119 }), 201);
    responder('get', '/prestamos/119', prestamo({ id: 119 }));
    const user = userEvent.setup();
    renderizarApp('/prestamos/nuevo', { conSesion: true });

    await user.type(
      await screen.findByLabelText('Buscar socio por número, documento o nombre'),
      'socia',
    );
    await user.click(await screen.findByRole('button', { name: 'Elegir' }));
    expect(screen.getByText('Socia, Sol')).toBeVisible();
    const combo = await screen.findByRole('combobox', { name: /Libro/ });
    await user.type(combo, 'Rayu');
    await user.click(await screen.findByRole('option', { name: /Rayuela/ }));
    expect(busquedas.at(-1).url.searchParams.get('q')).toBe('Rayu');
    const tabla = await screen.findByRole('table', { name: 'Ejemplares disponibles' });
    expect(within(tabla).getByText('Entre sedes')).toBeVisible();
    await user.click(within(tabla).getByRole('button', { name: 'Elegir' }));
    await user.click(screen.getByRole('button', { name: 'Registrar préstamo' }));

    expect(await screen.findByText(/Préstamo P-2026-000118 registrado/)).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ socio_id: 45, ejemplar_id: 305 });
  });
});
