import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
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
});
