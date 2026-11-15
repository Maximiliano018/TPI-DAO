import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ADMIN } from '../../../../tests/datos.js';
import { registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const PARAMETROS = [
  {
    clave: 'multa_por_dia',
    valor: '300.00',
    descripcion: 'Multa por día de atraso',
    actualizado_en: '2026-11-15T13:00:00Z',
    actualizado_por: { id: 1, nombre: 'Ana Admin' },
  },
  {
    clave: 'plazo_prestamo_local_dias',
    valor: '14',
    descripcion: 'Plazo del préstamo local en días',
    actualizado_en: null,
    actualizado_por: null,
  },
];

const HISTORIAL = {
  items: [
    {
      clave: 'multa_por_dia',
      descripcion: 'Multa por día de atraso',
      valor_anterior: '200.00',
      valor_nuevo: '300.00',
      usuario: { id: 1, nombre: 'Ana Admin' },
      fecha_hora: '2026-11-15T13:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  size: 10,
};

describe('Parámetros', () => {
  it('CA-ACC-18: el administrador ve quién cambió cada parámetro y el historial', async () => {
    sesionDe(ADMIN);
    responder('get', '/parametros', PARAMETROS);
    responder('get', '/parametros/historial', HISTORIAL);
    const cambios = registrar('put', '/parametros/plazo_prestamo_local_dias', {
      ...PARAMETROS[1],
      valor: '10',
    });
    const user = userEvent.setup();
    renderizarApp('/parametros', { conSesion: true });

    expect(await screen.findByText(/Modificado por Ana Admin el/)).toBeVisible();
    expect(screen.getByText('Valor inicial, sin cambios registrados')).toBeVisible();
    const tabla = await screen.findByRole('table', { name: 'Historial de cambios de parámetros' });
    expect(within(tabla).getByText('200.00 → 300.00')).toBeVisible();
    expect(within(tabla).getByText('Ana Admin')).toBeVisible();

    const plazo = screen.getByLabelText('Plazo del préstamo local en días');
    await user.clear(plazo);
    await user.type(plazo, '10');
    await user.click(
      screen.getByRole('button', { name: 'Guardar Plazo del préstamo local en días' }),
    );

    expect(await screen.findByText('Parámetro guardado')).toBeVisible();
    expect(cambios[0].cuerpo).toEqual({ valor: '10' });
  });
});
