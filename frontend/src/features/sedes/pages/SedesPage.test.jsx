import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  LOCALIDADES,
  SOCIO,
  pagina,
  sedeAdmin,
  sedeBasica,
  sedePublica,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const SEDES = [
  sedeAdmin(),
  sedeAdmin({ id: 2, codigo: 'NORTE', nombre: 'Sede Norte', abierta_ahora: false }),
  sedeAdmin({ id: 3, codigo: 'OESTE', nombre: 'Sede Oeste', estado: 'BAJA', baja: {} }),
];

function dePrueba(usuario, listado) {
  sesionDe(usuario);
  responder('get', '/localidades', LOCALIDADES);
  return registrar('get', '/sedes', listado);
}

describe('Listado de sedes', () => {
  it('administrador: tabla con acciones según el estado de cada sede', async () => {
    dePrueba(ADMIN, pagina(SEDES));
    const { container } = renderizarApp('/sedes', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Sedes' });
    const filas = within(tabla).getAllByRole('row').slice(1);
    expect(filas).toHaveLength(3);
    expect(within(filas[0]).getByText('CEN')).toBeInTheDocument();
    expect(within(filas[0]).getByRole('link', { name: 'Editar Sede Central' })).toHaveAttribute(
      'href',
      '/sedes/1/editar',
    );
    expect(
      within(filas[0]).getByRole('button', { name: 'Dar de baja Sede Central' }),
    ).toBeVisible();
    expect(within(filas[0]).queryByRole('button', { name: /Reactivar/ })).not.toBeInTheDocument();
    expect(within(filas[2]).getByRole('button', { name: 'Reactivar Sede Oeste' })).toBeVisible();
    expect(within(filas[2]).queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument();
    expect(within(filas[1]).getByText('Cerrada')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nueva sede' })).toHaveAttribute(
      'href',
      '/sedes/nueva',
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('bibliotecario: solo consulta, con filtro de estado y sin «Nueva sede»', async () => {
    dePrueba(BIBLIOTECARIO, pagina([sedeBasica()]));
    renderizarApp('/sedes', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Sedes' });
    expect(within(tabla).getByRole('link', { name: 'Ver Sede Central' })).toBeVisible();
    expect(screen.queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Dar de baja/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nueva sede' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Estado')).toHaveValue('ACTIVA');
  });

  it('socio: sin filtro ni columna de estado', async () => {
    const llamadas = dePrueba(SOCIO, pagina([sedePublica()]));
    renderizarApp('/sedes', { conSesion: true });

    await screen.findByRole('table', { name: 'Sedes' });
    expect(screen.queryByLabelText('Estado')).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Estado' })).not.toBeInTheDocument();
    expect(llamadas[0].url.searchParams.has('estado')).toBe(false);
  });

  it('los filtros de la URL llegan a la API y se pueden cambiar', async () => {
    const llamadas = dePrueba(ADMIN, pagina(SEDES));
    const user = userEvent.setup();
    renderizarApp('/sedes?estado=BAJA&q=cen&page=2', { conSesion: true });

    await screen.findByRole('table', { name: 'Sedes' });
    const primera = llamadas[0].url.searchParams;
    expect(primera.get('estado')).toBe('BAJA');
    expect(primera.get('q')).toBe('cen');
    expect(primera.get('page')).toBe('2');
    expect(screen.getByLabelText('Estado')).toHaveValue('BAJA');
    expect(screen.getByRole('searchbox', { name: 'Buscar' })).toHaveValue('cen');

    // Cambiar un filtro vuelve a la primera página.
    await user.selectOptions(screen.getByLabelText('Estado'), 'ACTIVA');
    await waitFor(() => {
      const ultima = llamadas.at(-1).url.searchParams;
      expect(ultima.get('estado')).toBe('ACTIVA');
      expect(ultima.get('page')).toBe('1');
    });

    await user.click(screen.getByRole('button', { name: 'Limpiar filtros' }));
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.has('q')).toBe(false));
  });

  it('la búsqueda espera antes de consultar y filtra por localidad', async () => {
    const llamadas = dePrueba(ADMIN, pagina(SEDES));
    const user = userEvent.setup();
    renderizarApp('/sedes', { conSesion: true });
    await screen.findByRole('table', { name: 'Sedes' });
    const antes = llamadas.length;

    await user.type(screen.getByRole('searchbox', { name: 'Buscar' }), 'norte');
    expect(llamadas.length).toBe(antes);
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('q')).toBe('norte'));

    await user.click(screen.getByRole('combobox', { name: 'Localidad' }));
    await user.click(await screen.findByRole('option', { name: /Villa María/ }));
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('localidad_id')).toBe('2'));
  });

  it('ordena por columna y pagina', async () => {
    const llamadas = dePrueba(ADMIN, pagina(SEDES, { total: 45, size: 20 }));
    const user = userEvent.setup();
    renderizarApp('/sedes', { conSesion: true });
    await screen.findByRole('table', { name: 'Sedes' });

    await user.click(screen.getByRole('button', { name: /Código/ }));
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('orden')).toBe('codigo'));
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('page')).toBe('2'));
  });

  it('vacío: ofrece limpiar los filtros', async () => {
    dePrueba(ADMIN, pagina([]));
    const user = userEvent.setup();
    renderizarApp('/sedes?q=zzz', { conSesion: true });

    expect(await screen.findByText('No hay sedes que coincidan')).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: 'Limpiar filtros' })[0]);
    await waitFor(() => expect(screen.getByRole('searchbox', { name: 'Buscar' })).toHaveValue(''));
  });

  it('error: muestra el mensaje y reintenta', async () => {
    sesionDe(ADMIN);
    responder('get', '/localidades', LOCALIDADES);
    registrar('get', '/sedes', (_llamada, llamadas) =>
      llamadas.length === 1 ? error(500, 'ERROR_INTERNO', 'Falló') : pagina(SEDES),
    );
    const user = userEvent.setup();
    renderizarApp('/sedes', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('table', { name: 'Sedes' })).toBeInTheDocument();
  });

  it('dar de baja desde la fila: pide motivo y envía la versión', async () => {
    dePrueba(ADMIN, pagina([sedeAdmin({ version: 4 })]));
    const baja = registrar('post', '/sedes/1/baja', sedeAdmin({ estado: 'BAJA' }));
    const user = userEvent.setup();
    renderizarApp('/sedes', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja Sede Central' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Dar de baja Sede Central' });
    const confirmar = within(dialogo).getByRole('button', { name: 'Dar de baja' });
    expect(confirmar).toBeDisabled();
    await user.type(within(dialogo).getByLabelText(/Motivo de la baja/), 'Cierre definitivo');
    expect(within(dialogo).getByText(/17\/300/)).toBeInTheDocument();
    await user.click(confirmar);

    await waitFor(() => expect(baja).toHaveLength(1));
    expect(baja[0].cuerpo).toEqual({ motivo: 'Cierre definitivo', version: 4 });
    expect(await screen.findByText('Sede dada de baja')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });
});
