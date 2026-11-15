import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  SOCIO,
  libro,
  pagina,
  prestamo,
  reserva,
  sedePublica,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const DISPONIBILIDAD_VACIA = {
  libro_id: 12,
  titulo: 'Rayuela',
  total_red: { totales: 1, disponibles: 0 },
  por_sede: [],
};

describe('Reservas', () => {
  it('CA-RES-13: el socio ve sus reservas con su lugar en la cola y puede cancelar', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    responder('get', '/reservas', pagina([reserva()]));
    const llamadas = registrar('post', '/reservas/9/cancelar', reserva({ estado: 'CANCELADA' }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/', { conSesion: true });

    await user.click(await screen.findByRole('link', { name: 'Mis reservas' }));
    const tabla = await screen.findByRole('table', { name: 'Reservas' });
    expect(within(tabla).getByText('Lugar 2 en la cola')).toBeVisible();
    expect(within(tabla).getByText('En espera')).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();

    await user.click(
      within(tabla).getByRole('button', { name: 'Cancelar la reserva RS-2026-000009' }),
    );
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancelar reserva' }),
    );
    expect(await screen.findByText('Reserva cancelada')).toBeVisible();
    expect(llamadas).toHaveLength(1);
  });

  it('el socio reserva desde la ficha del libro eligiendo la sede de retiro', async () => {
    sesionDe(SOCIO);
    responder('get', '/libros/12', libro({ disponibles: 0 }));
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD_VACIA);
    responder('get', '/sedes', pagina([sedePublica()]));
    const llamadas = registrar('post', '/reservas', reserva({ posicion_en_cola: 3 }), 201);
    const user = userEvent.setup();
    renderizarApp('/catalogo/12', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Reservar' }));
    const dialogo = screen.getByRole('dialog');
    await user.selectOptions(within(dialogo).getByLabelText(/Sede de retiro/), '1');
    await user.click(within(dialogo).getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByText(/lugar 3 en la cola/)).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ libro_id: 12, sede_retiro_id: 1 });
  });

  it('CA-RES-01: con disponibles en la sede se informa que corresponde un préstamo', async () => {
    sesionDe(SOCIO);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD_VACIA);
    responder('get', '/sedes', pagina([sedePublica()]));
    responder('post', '/reservas', () =>
      error(
        409,
        'HAY_EJEMPLARES_DISPONIBLES',
        'Hay ejemplares disponibles: corresponde un préstamo.',
      ),
    );
    const user = userEvent.setup();
    renderizarApp('/catalogo/12', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Reservar' }));
    const dialogo = screen.getByRole('dialog');
    await user.selectOptions(within(dialogo).getByLabelText(/Sede de retiro/), '1');
    await user.click(within(dialogo).getByRole('button', { name: 'Reservar' }));
    expect(await within(dialogo).findByText(/corresponde un préstamo/)).toBeVisible();
  });

  it('CA-RES-12: el bibliotecario entrega una reserva lista para retirar en su sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/sedes', pagina([sedePublica()]));
    responder(
      'get',
      '/reservas',
      pagina([
        reserva({
          estado: 'DISPONIBLE_PARA_RETIRO',
          posicion_en_cola: null,
          ejemplar_id: 301,
          codigo_ejemplar: 'CEN-000123',
          vencimiento_retiro: '2026-11-13',
        }),
      ]),
    );
    const llamadas = registrar('post', '/reservas/9/retirar', prestamo({ estado: 'ACTIVO' }));
    const user = userEvent.setup();
    renderizarApp('/reservas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Reservas' });
    expect(within(tabla).getByText('Retirar hasta el 13/11/2026')).toBeVisible();
    await user.click(within(tabla).getByRole('button', { name: 'Entregar' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Entregar' }));

    expect(await screen.findByText('Reserva entregada')).toBeVisible();
    expect(llamadas).toHaveLength(1);
  });

  it('CA-RES-22: el bibliotecario ve por defecto las reservas que se retiran en su sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/sedes', pagina([sedePublica()]));
    const llamadas = registrar(
      'get',
      '/reservas',
      pagina([reserva(), reserva({ id: 10, numero: 'RS-2026-000010', sede_retiro_id: 2 })]),
    );
    const user = userEvent.setup();
    renderizarApp('/reservas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Reservas' });
    expect(llamadas[0].url.searchParams.get('sede_retiro_id')).toBe('1');
    // Solo cancela las de su sede (CA-RES-17).
    expect(
      within(tabla).getByRole('button', { name: 'Cancelar la reserva RS-2026-000009' }),
    ).toBeVisible();
    expect(
      within(tabla).queryByRole('button', { name: 'Cancelar la reserva RS-2026-000010' }),
    ).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Sede de retiro'), 'todas');
    await vi.waitFor(() =>
      expect(llamadas.at(-1).url.searchParams.has('sede_retiro_id')).toBe(false),
    );
  });

  it('CA-ACC-19: el administrador consulta todas las reservas y puede cancelarlas', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes', pagina([sedePublica()]));
    responder('get', '/reservas', pagina([reserva()]));
    renderizarApp('/reservas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Reservas' });
    expect(within(tabla).getByRole('link', { name: 'RS-2026-000009' })).toBeVisible();
    expect(within(tabla).getByRole('button', { name: /Cancelar/ })).toBeVisible();
  });

  it('CA-RES-22: el personal ve la cola del libro en su ficha, en orden de llegada', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros/12', libro({ disponibles: 0 }));
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD_VACIA);
    responder('get', '/ejemplares', pagina([]));
    const llamadas = registrar(
      'get',
      '/reservas',
      pagina([
        reserva({ posicion_en_cola: 1 }),
        reserva({ id: 10, numero: 'RS-2026-000010', socio: 'Otro Socio', posicion_en_cola: 2 }),
      ]),
    );
    renderizarApp('/catalogo/12', { conSesion: true });

    const cola = await screen.findByRole('table', { name: 'Cola de reservas' });
    const filas = within(cola).getAllByRole('row').slice(1);
    expect(filas.map((f) => within(f).getAllByRole('cell')[0].textContent)).toEqual(['1', '2']);
    expect(Object.fromEntries(llamadas[0].url.searchParams)).toMatchObject({
      libro_id: '12',
      estado: 'PENDIENTE',
      orden: 'cola',
    });
  });

  it('CA-RES-14: con ejemplares disponibles en la red no se ofrece reservar', async () => {
    sesionDe(SOCIO);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', {
      ...DISPONIBILIDAD_VACIA,
      total_red: { totales: 2, disponibles: 1 },
      por_sede: [
        {
          sede_id: 2,
          sede: 'Sede Norte',
          totales: 2,
          disponibles: 1,
          prestados: 1,
          reservados: 0,
          en_transito: 0,
          otros: 0,
        },
      ],
    });
    renderizarApp('/catalogo/12', { conSesion: true });

    expect(await screen.findByRole('button', { name: 'Pedir préstamo' })).toBeVisible();
    expect(await screen.findByText(/1 de 2 ejemplares disponibles/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Reservar' })).not.toBeInTheDocument();
  });
});
