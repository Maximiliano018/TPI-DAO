import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { ADMIN, BIBLIOTECARIO, SOCIO, reserva } from '../../../../tests/datos.js';
import { registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const HISTORIAL = [
  {
    estado_anterior: null,
    estado_nuevo: 'PENDIENTE',
    fecha_hora: '2026-11-10T15:00:00Z',
    autor: 'Personal de la biblioteca',
    usuario: null,
    observacion: 'Reserva registrada',
  },
  {
    estado_anterior: 'PENDIENTE',
    estado_nuevo: 'DISPONIBLE_PARA_RETIRO',
    fecha_hora: '2026-11-11T10:00:00Z',
    autor: 'Sistema',
    usuario: null,
    observacion: 'Ejemplar CEN-000123 asignado: retirar hasta el 14/11/2026',
  },
];

const DISPONIBLE = {
  estado: 'DISPONIBLE_PARA_RETIRO',
  posicion_en_cola: null,
  ejemplar_id: 301,
  codigo_ejemplar: 'CEN-000123',
  vencimiento_retiro: '2026-11-14',
};

describe('Ficha de la reserva', () => {
  it('CA-RES-19: el socio ve el historial con su autor y cancela con motivo', async () => {
    sesionDe(SOCIO);
    responder('get', '/reservas/9', reserva({ ...DISPONIBLE, historial: HISTORIAL }));
    const llamadas = registrar('post', '/reservas/9/cancelar', reserva({ estado: 'CANCELADA' }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/reservas/9', { conSesion: true });

    const historial = await screen.findByRole('list', { name: 'Historial de la reserva' });
    expect(within(historial).getByText(/Sistema/)).toBeVisible();
    expect(within(historial).getByText(/Personal de la biblioteca/)).toBeVisible();
    expect(screen.getByText(/Podés retirar/)).toBeVisible();
    expect(screen.queryByText('Registrada por')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await user.click(screen.getByRole('button', { name: 'Cancelar reserva' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Ya lo conseguí');
    await user.click(within(dialogo).getByRole('button', { name: 'Cancelar reserva' }));

    expect(await screen.findByText('Reserva cancelada')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ motivo: 'Ya lo conseguí' });
  });

  it('CA-RES-17: el bibliotecario de la sede de retiro entrega y cancela; ve quién la registró', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/reservas/9',
      reserva({
        ...DISPONIBLE,
        historial: HISTORIAL,
        registrada_por: { id: 3, nombre: 'Sol Socia' },
      }),
    );
    renderizarApp('/reservas/9', { conSesion: true });

    expect(await screen.findByRole('button', { name: 'Entregar' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Cancelar reserva' })).toBeVisible();
    expect(screen.getByText('Registrada por').nextSibling).toHaveTextContent('Sol Socia');
  });

  it('CA-ACC-19: el administrador opera en cualquier sede: puede cancelar la reserva', async () => {
    sesionDe(ADMIN);
    responder('get', '/reservas/9', reserva({ historial: HISTORIAL.slice(0, 1) }));
    renderizarApp('/reservas/9', { conSesion: true });

    expect(await screen.findByText(/Lugar 2 en la cola/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Cancelar reserva' })).toBeVisible();
  });

  it('CA-RES-17: el bibliotecario no cancela una reserva que se retira en otra sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/reservas/9',
      reserva({ sede_retiro_id: 2, sede_retiro: 'Sede Norte', historial: HISTORIAL.slice(0, 1) }),
    );
    renderizarApp('/reservas/9', { conSesion: true });

    expect(await screen.findByText(/Lugar 2 en la cola/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Cancelar reserva' })).not.toBeInTheDocument();
  });
});
