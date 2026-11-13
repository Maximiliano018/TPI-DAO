import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { BIBLIOTECARIO, ejemplar, libro, pagina, sedeAdmin } from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

describe('Ejemplares', () => {
  it('CA-CAT-06: la ficha muestra datos e historial y las acciones según el estado', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/ejemplares/301',
      ejemplar({
        estado: 'EN_REVISION',
        historial: [
          ...ejemplar().historial,
          {
            estado_anterior: 'DISPONIBLE',
            estado_nuevo: 'EN_REVISION',
            fecha_hora: '2026-10-20T15:30:00Z',
            usuario: { id: 2, nombre: 'Lucía Gómez' },
            observacion: 'Devuelto con la tapa rota',
          },
        ],
      }),
    );
    const { container } = renderizarApp('/ejemplares/301', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'CEN-000123' })).toBeVisible();
    const historial = screen.getByRole('list', { name: 'Historial del ejemplar' });
    const pasos = within(historial).getAllByRole('listitem');
    expect(pasos).toHaveLength(2);
    expect(within(pasos[0]).getByText('En revisión')).toBeVisible();
    expect(within(pasos[0]).getByText('Devuelto con la tapa rota')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Marcar como reparado' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Dar de baja' })).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('CA-CAT-05: un ejemplar de otra sede no muestra acciones al bibliotecario', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/ejemplares/302', ejemplar({ id: 302, sede_propietaria_id: 2 }));
    renderizarApp('/ejemplares/302', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'CEN-000123' });
    expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Dar de baja' })).not.toBeInTheDocument();
  });

  it('CA-CAT-07: la baja bloqueada muestra el motivo del servidor', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/ejemplares/301', ejemplar());
    responder('post', '/ejemplares/301/baja', () =>
      error(
        409,
        'EJEMPLAR_NO_DISPONIBLE',
        'El ejemplar CEN-000123 no se puede dar de baja: está prestado.',
      ),
    );
    const user = userEvent.setup();
    renderizarApp('/ejemplares/301', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Hojas arrancadas');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    expect(await within(dialogo).findByText(/está prestado/)).toBeVisible();
  });

  it('el bibliotecario carga un ejemplar en su sede desde el libro', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros', pagina([libro()]));
    responder('get', '/sedes', pagina([sedeAdmin()]));
    const llamadas = registrar('post', '/ejemplares', ejemplar(), 201);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', {
      libro_id: 12,
      titulo: 'Rayuela',
      total_red: { totales: 1, disponibles: 1 },
      por_sede: [],
    });
    responder('get', '/ejemplares', pagina([ejemplar()]));
    const user = userEvent.setup();
    renderizarApp('/ejemplares/nuevo?libro_id=12', { conSesion: true });

    expect(await screen.findByRole('combobox', { name: /Libro/ })).toHaveValue('Rayuela');
    expect(screen.getByText(/Se carga en su sede \(Sede Central\)/)).toBeVisible();
    await user.type(screen.getByLabelText(/Código de inventario/), 'cen-000123');
    await user.click(screen.getByRole('button', { name: 'Cargar ejemplar' }));

    expect(await screen.findByText('Ejemplar CEN-000123 cargado')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({
      libro_id: 12,
      codigo_inventario: 'cen-000123',
      estado_fisico: 'BUENO',
      observaciones: null,
      sede_id: null,
    });
  });

  it('CA-CAT-02: un código repetido se marca en el campo', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros', pagina([libro()]));
    responder('get', '/sedes', pagina([sedeAdmin()]));
    responder('post', '/ejemplares', () =>
      error(409, 'EJEMPLAR_CODIGO_DUPLICADO', 'Ya existe un ejemplar con ese código.'),
    );
    const user = userEvent.setup();
    renderizarApp('/ejemplares/nuevo?libro_id=12', { conSesion: true });

    await user.type(await screen.findByLabelText(/Código de inventario/), 'CEN-000123');
    await user.click(screen.getByRole('button', { name: 'Cargar ejemplar' }));

    expect(
      await screen.findByText('Ya existe un ejemplar con ese código de inventario en la red'),
    ).toBeVisible();
  });
});
