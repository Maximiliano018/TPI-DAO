import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { BIBLIOTECARIO, SOCIO, multa, pagina, prestamo } from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const ACTIVO = prestamo({
  estado: 'VENCIDO',
  fecha_inicio: '2026-10-27',
  fecha_vencimiento: '2026-11-10',
});

describe('Devoluciones', () => {
  it('CA-DEV-06: el bibliotecario registra una devolución tardía y ve la multa', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/prestamos/118', ACTIVO);
    const llamadas = registrar(
      'post',
      '/prestamos/118/devolucion',
      {
        prestamo: { ...ACTIVO, estado: 'DEVUELTO' },
        devolucion: { id: 60, dias_atraso: 5, estado_fisico_recibido: 'BUENO' },
        multa: multa(),
        remito_retorno: null,
        reserva_asignada: null,
        socio: { id: 45, estado: 'INHABILITADO', motivo: 'MULTA_IMPAGA' },
      },
      201,
    );
    const user = userEvent.setup();
    renderizarApp('/prestamos/118', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Registrar devolución' }));
    const dialogo = screen.getByRole('dialog');
    await user.click(within(dialogo).getByRole('button', { name: 'Registrar devolución' }));

    expect(await screen.findByText(/multa de \$\s?1\.000,00 por 5 día/)).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({
      estado_fisico: 'BUENO',
      observaciones: null,
      fecha_hora: null,
    });
  });

  it('un daño exige observaciones y el error del servidor se muestra en el diálogo', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/prestamos/118', ACTIVO);
    responder('post', '/prestamos/118/devolucion', () =>
      error(409, 'TRANSICION_INVALIDA', 'El préstamo ya fue devuelto.'),
    );
    const user = userEvent.setup();
    renderizarApp('/prestamos/118', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Registrar devolución' }));
    const dialogo = screen.getByRole('dialog');
    await user.selectOptions(within(dialogo).getByLabelText(/Estado en que llega/), 'DANADO');
    const confirmar = within(dialogo).getByRole('button', { name: 'Registrar devolución' });
    expect(confirmar).toBeDisabled();

    await user.type(within(dialogo).getByLabelText(/Observaciones/), 'Tapa rota');
    await user.click(confirmar);

    expect(await within(dialogo).findByText('El préstamo ya fue devuelto.')).toBeVisible();
  });

  it('CA-DEV-03: en otra sede no se ofrece registrar la devolución', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/prestamos/118', {
      ...ACTIVO,
      sede_destino_id: 2,
      sede_destino: 'Sede Norte',
      tipo: 'INTERBIBLIOTECARIO',
    });
    renderizarApp('/prestamos/118', { conSesion: true });

    expect(await screen.findByText('Sede Norte')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Registrar devolución' })).not.toBeInTheDocument();
  });

  it('un préstamo devuelto muestra la devolución y su multa', async () => {
    sesionDe(SOCIO);
    responder(
      'get',
      '/prestamos/118',
      prestamo({
        estado: 'DEVUELTO',
        devolucion: {
          id: 60,
          prestamo_id: 118,
          sede_id: 1,
          fecha_hora: '2026-11-15T15:00:00Z',
          estado_fisico_recibido: 'REGULAR',
          dias_atraso: 5,
          observaciones: 'Hojas marcadas',
          registrada_por: { id: 2, nombre: 'Lucía Gómez' },
        },
        multa: multa(),
      }),
    );
    renderizarApp('/prestamos/118', { conSesion: true });

    expect(await screen.findByText('Hojas marcadas')).toBeVisible();
    expect(screen.getByText('5 día(s)')).toBeVisible();
    expect(screen.getByText('Pendiente')).toBeVisible();
  });
});

describe('Multas', () => {
  it('CA-DEV-16: el socio ve sus multas, sin columna de socio ni botón para saldar', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    responder('get', '/multas', pagina([multa()]));
    const user = userEvent.setup();
    const { container } = renderizarApp('/', { conSesion: true });

    await user.click(await screen.findByRole('link', { name: 'Mis multas' }));
    const tabla = await screen.findByRole('table', { name: 'Multas' });
    const encabezados = within(tabla)
      .getAllByRole('columnheader')
      .map((c) => c.textContent);
    expect(encabezados).not.toContain('Socio');
    expect(encabezados).not.toContain('Acciones');
    expect(within(tabla).getByText('Pendiente')).toBeVisible();
    expect(screen.getByText(/no puede pedir préstamos ni reservas/)).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('CA-DEV-10: el bibliotecario salda una multa pendiente', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/multas',
      pagina([
        multa(),
        multa({
          id: 15,
          estado: 'SALDADA',
          fecha_saldada: '2026-11-16T12:00:00Z',
          numero_prestamo: 'P-2026-000119',
        }),
      ]),
    );
    const llamadas = registrar('post', '/multas/14/saldar', multa({ estado: 'SALDADA' }));
    const user = userEvent.setup();
    renderizarApp('/multas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Multas' });
    expect(within(tabla).getByText('Saldada el 16/11/2026')).toBeVisible();
    await user.click(
      within(tabla).getByRole('button', { name: 'Saldar la multa del préstamo P-2026-000118' }),
    );
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Marcar saldada' }),
    );

    expect(await screen.findByText('Multa saldada')).toBeVisible();
    expect(llamadas).toHaveLength(1);
  });
});
