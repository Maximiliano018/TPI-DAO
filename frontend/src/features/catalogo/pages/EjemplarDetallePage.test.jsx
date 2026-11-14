import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  ejemplar,
  libro,
  pagina,
  sedeAdmin,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

describe('Ejemplares', () => {
  it('CA-CAT-06, CA-CAT-14: la ficha muestra el historial con sus cambios y las acciones', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/ejemplares/301',
      ejemplar({
        estado: 'EN_REVISION',
        historial: [
          ...ejemplar().historial,
          {
            tipo: 'TRASLADO',
            estado_anterior: 'EN_TRANSITO',
            estado_nuevo: 'EN_TRANSITO',
            fecha_hora: '2026-10-18T15:30:00Z',
            usuario: { id: 2, nombre: 'Lucía Gómez' },
            observacion: 'Recibido en R-2026-000004',
            cambios: [
              { campo: 'sede_actual', antes: 'Sede Norte', despues: 'Sede Central' },
              { campo: 'sede_propietaria', antes: 'Sede Norte', despues: 'Sede Central' },
            ],
          },
          {
            tipo: 'CAMBIO_DE_ESTADO',
            estado_anterior: 'DISPONIBLE',
            estado_nuevo: 'EN_REVISION',
            fecha_hora: '2026-10-20T15:30:00Z',
            usuario: { id: 2, nombre: 'Lucía Gómez' },
            observacion: 'Devuelto con la tapa rota',
            cambios: [{ campo: 'estado_fisico', antes: 'BUENO', despues: 'DANADO' }],
          },
        ],
      }),
    );
    const { container } = renderizarApp('/ejemplares/301', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'CEN-000123' })).toBeVisible();
    const historial = screen.getByRole('list', { name: 'Historial del ejemplar' });
    // Solo los pasos de la línea de tiempo (cada paso tiene su propia lista de cambios).
    const pasos = within(historial)
      .getAllByRole('listitem')
      .filter((li) => li.parentElement === historial);
    expect(pasos).toHaveLength(3);
    expect(within(pasos[0]).getByText('En revisión')).toBeVisible();
    expect(within(pasos[0]).getByText('Devuelto con la tapa rota')).toBeVisible();
    expect(within(pasos[0]).getByText('Estado físico: Bueno → Dañado')).toBeVisible();
    expect(within(pasos[1]).getByText('Traslado a otra sede')).toBeVisible();
    expect(within(pasos[1]).getByText('Sede propietaria: Sede Norte → Sede Central')).toBeVisible();
    expect(within(pasos[2]).getByText('Alta en el catálogo')).toBeVisible();
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
    responder('get', '/libros', pagina([]));
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

    const campo = await screen.findByRole('combobox', { name: /Libro/ });
    await waitFor(() => expect(campo).toHaveValue('Rayuela'));
    expect(screen.getByText(/Se carga en su sede \(Sede Central\)/)).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Crear el libro' })).not.toBeInTheDocument();
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

  it('el libro se busca en el servidor y el administrador puede crearlo si no está', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes', pagina([sedeAdmin()]));
    const busquedas = registrar('get', '/libros', ({ url }) =>
      pagina(
        url.searchParams.get('q') === 'borges'
          ? [libro({ id: 40, titulo: 'Ficciones', autores: ['Jorge Luis Borges'] })]
          : [],
      ),
    );
    const user = userEvent.setup();
    renderizarApp('/ejemplares/nuevo', { conSesion: true });

    const campo = await screen.findByRole('combobox', { name: /Libro/ });
    expect(screen.getByRole('link', { name: 'Crear el libro' })).toHaveAttribute(
      'href',
      '/catalogo/nuevo',
    );
    await user.type(campo, 'borges');
    // Lo encuentra por autor: la búsqueda la resuelve el servidor, no el texto de la opción.
    await user.click(await screen.findByRole('option', { name: /Ficciones/ }));
    expect(campo).toHaveValue('Ficciones');
    expect(busquedas.at(-1).url.searchParams.get('q')).toBe('borges');
  });

  it('CA-CAT-02: un código repetido se marca en el campo', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros', pagina([]));
    responder('get', '/libros/12', libro());
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
