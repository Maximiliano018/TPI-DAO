import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  CATEGORIAS,
  SOCIO,
  ejemplar,
  libro,
  pagina,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const DISPONIBILIDAD = {
  libro_id: 12,
  titulo: 'Rayuela',
  total_red: { totales: 3, disponibles: 1 },
  por_sede: [
    {
      sede_id: 1,
      sede: 'Sede Central',
      totales: 3,
      disponibles: 1,
      prestados: 1,
      reservados: 0,
      en_transito: 1,
      otros: 0,
    },
  ],
};

describe('Catálogo', () => {
  it('el socio busca libros y ve cuántos hay disponibles, sin acciones de alta', async () => {
    sesionDe(SOCIO);
    responder('get', '/categorias', CATEGORIAS);
    const llamadas = registrar(
      'get',
      '/libros',
      pagina([libro(), libro({ id: 13, titulo: 'Facundo', disponibles: 0, ejemplares: 0 })]),
    );
    const user = userEvent.setup();
    const { container } = renderizarApp('/catalogo', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Libros' });
    const filas = within(tabla).getAllByRole('row').slice(1);
    expect(within(filas[0]).getByRole('link', { name: 'Rayuela' })).toHaveAttribute(
      'href',
      '/catalogo/12',
    );
    expect(within(filas[0]).getByText('1 de 3')).toBeInTheDocument();
    expect(within(filas[1]).getByText('Sin ejemplares')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nuevo libro' })).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await user.selectOptions(screen.getByLabelText('Categoría'), '2');
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('categoria_id')).toBe('2'));
    await user.selectOptions(screen.getByLabelText('Tipo de material'), 'REVISTA');
    await waitFor(() =>
      expect(llamadas.at(-1).url.searchParams.get('tipo_material')).toBe('REVISTA'),
    );
  });

  it('CU-CAT-05 A3: sin disponibles en su sede, avisa que puede pedirse a otra sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', {
      ...DISPONIBILIDAD,
      total_red: { totales: 3, disponibles: 2 },
      por_sede: [
        { ...DISPONIBILIDAD.por_sede[0], disponibles: 0, prestados: 1, en_transito: 0, totales: 1 },
        {
          ...DISPONIBILIDAD.por_sede[0],
          sede_id: 2,
          sede: 'Sede Norte',
          disponibles: 2,
          prestados: 0,
          en_transito: 0,
          totales: 2,
        },
      ],
    });
    responder('get', '/ejemplares', pagina([]));
    renderizarApp('/catalogo/12', { conSesion: true });

    expect(
      await screen.findByText(/se puede pedir como préstamo interbibliotecario/),
    ).toBeVisible();
  });

  it('CA-CAT-16: «Eliminar» solo aparece si el libro no tiene ningún ejemplar', async () => {
    sesionDe(ADMIN);
    responder('get', '/libros/12', libro({ ejemplares: 0, eliminable: false }));
    responder('get', '/libros/13', libro({ id: 13, ejemplares: 0, eliminable: true }));
    responder('get', '/libros/:id/disponibilidad', DISPONIBILIDAD);
    responder('get', '/ejemplares', pagina([]));
    const { unmount } = renderizarApp('/catalogo/12', { conSesion: true });

    // Rayuela solo tiene ejemplares dados de baja: siguen siendo historial.
    await screen.findByRole('link', { name: 'Editar' });
    expect(screen.queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument();
    unmount();

    renderizarApp('/catalogo/13', { conSesion: true });
    expect(await screen.findByRole('button', { name: 'Eliminar' })).toBeVisible();
  });

  it('CA-CAT-19: al editar un libro se envía su versión', async () => {
    sesionDe(ADMIN);
    responder('get', '/categorias', CATEGORIAS);
    responder('get', '/libros/12', libro({ version: 4 }));
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD);
    responder('get', '/ejemplares', pagina([]));
    const llamadas = registrar('put', '/libros/12', libro({ version: 5 }));
    const user = userEvent.setup();
    renderizarApp('/catalogo/12/editar', { conSesion: true });

    const editorial = await screen.findByLabelText(/Editorial/);
    await user.clear(editorial);
    await user.type(editorial, 'Alfaguara');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));

    expect(await screen.findByText('Libro guardado')).toBeVisible();
    expect(llamadas[0].cuerpo).toMatchObject({ editorial: 'Alfaguara', version: 4 });
  });

  it('CA-CAT-10: la ficha muestra la disponibilidad por sede y los ejemplares al personal', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD);
    responder('get', '/ejemplares', pagina([ejemplar()]));
    renderizarApp('/catalogo/12', { conSesion: true });

    const disponibilidad = await screen.findByRole('table', { name: 'Disponibilidad por sede' });
    const [fila] = within(disponibilidad).getAllByRole('row').slice(1);
    expect(
      within(fila)
        .getAllByRole('cell')
        .map((c) => c.textContent),
    ).toEqual(['Sede Central', '1', '1', '0', '1', '3']);
    const ejemplares = await screen.findByRole('table', { name: 'Ejemplares' });
    expect(within(ejemplares).getByRole('link', { name: 'CEN-000123' })).toHaveAttribute(
      'href',
      '/ejemplares/301',
    );
    expect(screen.getByRole('link', { name: 'Agregar ejemplar' })).toHaveAttribute(
      'href',
      '/ejemplares/nuevo?libro_id=12',
    );
    // Editar y eliminar libros es del administrador.
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
  });

  it('el administrador crea un libro con autores uno por línea', async () => {
    sesionDe(ADMIN);
    responder('get', '/categorias', CATEGORIAS);
    const llamadas = registrar('post', '/libros', libro(), 201);
    responder('get', '/libros/12', libro());
    responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD);
    responder('get', '/ejemplares', pagina([]));
    const user = userEvent.setup();
    renderizarApp('/catalogo/nuevo', { conSesion: true });

    await user.type(await screen.findByLabelText(/Título/), 'Rayuela');
    await user.type(screen.getByLabelText(/Autores/), 'Julio Cortázar{Enter}Otro Autor');
    await user.type(screen.getByLabelText(/ISBN/), '978-950-07-0578-3');
    await user.selectOptions(screen.getByLabelText(/Categoría/), '1');
    await user.click(screen.getByRole('button', { name: 'Crear libro' }));

    expect(await screen.findByText('Libro creado')).toBeVisible();
    expect(llamadas[0].cuerpo).toMatchObject({
      titulo: 'Rayuela',
      autores: ['Julio Cortázar', 'Otro Autor'],
      isbn: '978-950-07-0578-3',
      categoria_id: 1,
      tipo_material: 'LIBRO',
      editorial: null,
      anio_edicion: null,
    });
  });

  it('CA-CAT-01: un ISBN repetido enlaza al libro existente', async () => {
    sesionDe(ADMIN);
    responder('get', '/categorias', CATEGORIAS);
    responder('post', '/libros', () =>
      error(409, 'LIBRO_DUPLICADO', 'Ya existe el libro «Rayuela» con el ISBN 9789500705783.', [
        { campo: 'isbn', problema: 'duplicado', libro_id: 12 },
      ]),
    );
    const user = userEvent.setup();
    renderizarApp('/catalogo/nuevo', { conSesion: true });

    await user.type(await screen.findByLabelText(/Título/), 'Rayuela');
    await user.type(screen.getByLabelText(/Autores/), 'Julio Cortázar');
    await user.selectOptions(screen.getByLabelText(/Categoría/), '1');
    await user.click(screen.getByRole('button', { name: 'Crear libro' }));

    expect(await screen.findByText(/Ya existe el libro «Rayuela»/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Ver el libro existente' })).toHaveAttribute(
      'href',
      '/catalogo/12',
    );
  });
});
