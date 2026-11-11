import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  pagina,
  sedeAdmin,
  usuarioPersonal,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const USUARIOS = [
  usuarioPersonal(),
  usuarioPersonal({
    id: 11,
    username: 'ana.admin',
    nombre: 'Ana Admin',
    rol: 'ADMIN',
    sede_id: null,
    sede: null,
  }),
  usuarioPersonal({ id: 12, username: 'pedro.baja', nombre: 'Pedro Baja', activo: false }),
];

function preparar(listado = pagina(USUARIOS)) {
  sesionDe(ADMIN);
  responder('get', '/sedes', pagina([sedeAdmin(), sedeAdmin({ id: 2, nombre: 'Sede Norte' })]));
  return registrar('get', '/usuarios', listado);
}

describe('Listado de usuarios', () => {
  it('tabla con rol, sede, estado y acciones según el estado', async () => {
    preparar();
    const { container } = renderizarApp('/usuarios', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Usuarios' });
    const filas = within(tabla).getAllByRole('row').slice(1);
    expect(filas).toHaveLength(3);
    expect(within(filas[0]).getByText('lucia.gomez')).toBeInTheDocument();
    expect(within(filas[0]).getByText('Bibliotecario')).toBeInTheDocument();
    expect(within(filas[0]).getByText('Sede Central')).toBeInTheDocument();
    expect(within(filas[0]).getByText('Activo')).toBeInTheDocument();
    expect(within(filas[0]).getByRole('link', { name: 'Editar a Lucía Gómez' })).toHaveAttribute(
      'href',
      '/usuarios/10/editar',
    );
    expect(
      within(filas[0]).getByRole('button', { name: 'Dar de baja a Lucía Gómez' }),
    ).toBeVisible();
    expect(within(filas[0]).queryByRole('button', { name: /Reactivar/ })).not.toBeInTheDocument();
    // Un administrador no tiene sede: opera en toda la red.
    expect(within(filas[1]).getByText('Toda la red')).toBeInTheDocument();
    expect(within(filas[2]).getByText('Dado de baja')).toBeInTheDocument();
    expect(within(filas[2]).getByRole('button', { name: 'Reactivar a Pedro Baja' })).toBeVisible();
    expect(within(filas[2]).queryByRole('button', { name: /Dar de baja/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nuevo usuario' })).toHaveAttribute(
      'href',
      '/usuarios/nuevo',
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('los filtros de la URL (incluido el enlace desde la baja de sede) llegan a la API', async () => {
    const llamadas = preparar();
    renderizarApp('/usuarios?sede_id=1&estado=activos&rol=BIBLIOTECARIO&q=luc', {
      conSesion: true,
    });

    await screen.findByRole('table', { name: 'Usuarios' });
    const params = llamadas[0].url.searchParams;
    expect(params.get('sede_id')).toBe('1');
    expect(params.get('activo')).toBe('true');
    expect(params.get('rol')).toBe('BIBLIOTECARIO');
    expect(params.get('q')).toBe('luc');
    expect(screen.getByLabelText('Sede')).toHaveValue('1');
    expect(screen.getByLabelText('Estado')).toHaveValue('activos');
    expect(screen.getByLabelText('Rol')).toHaveValue('BIBLIOTECARIO');
  });

  it('cambiar filtros consulta de nuevo; «dados de baja» envía activo=false', async () => {
    const llamadas = preparar();
    const user = userEvent.setup();
    renderizarApp('/usuarios?page=2', { conSesion: true });
    await screen.findByRole('table', { name: 'Usuarios' });

    await user.selectOptions(screen.getByLabelText('Estado'), 'baja');
    await waitFor(() => {
      const params = llamadas.at(-1).url.searchParams;
      expect(params.get('activo')).toBe('false');
      expect(params.get('page')).toBe('1');
    });
    await user.selectOptions(screen.getByLabelText('Sede'), '2');
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.get('sede_id')).toBe('2'));
    await user.click(screen.getByRole('button', { name: 'Limpiar filtros' }));
    await waitFor(() => expect(llamadas.at(-1).url.searchParams.has('activo')).toBe(false));
  });

  it('vacío y error con reintento', async () => {
    preparar(pagina([]));
    renderizarApp('/usuarios?q=zzz', { conSesion: true });
    expect(await screen.findByText('No hay usuarios que coincidan')).toBeInTheDocument();
  });

  it('error: reintenta', async () => {
    preparar((_llamada, llamadas) =>
      llamadas.length === 1 ? error(500, 'ERROR_INTERNO', 'Falló') : pagina(USUARIOS),
    );
    const user = userEvent.setup();
    renderizarApp('/usuarios', { conSesion: true });
    await user.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('table', { name: 'Usuarios' })).toBeInTheDocument();
  });

  it('dar de baja pide confirmación y refresca', async () => {
    preparar();
    const baja = registrar('post', '/usuarios/10/baja', usuarioPersonal({ activo: false }));
    const user = userEvent.setup();
    renderizarApp('/usuarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja a Lucía Gómez' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Dar de baja a Lucía Gómez' });
    expect(dialogo).toHaveTextContent('Se conserva su historial');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    await waitFor(() => expect(baja).toHaveLength(1));
    expect(await screen.findByText('Usuario dado de baja')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('el administrador no puede darse de baja a sí mismo: se muestra el motivo', async () => {
    preparar();
    responder(
      'post',
      '/usuarios/11/baja',
      () =>
        error(422, 'VALIDACION', 'No puede darse de baja a sí mismo.', [
          { campo: 'id', problema: 'No puede darse de baja a sí mismo.' },
        ]),
      422,
    );
    const user = userEvent.setup();
    renderizarApp('/usuarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja a Ana Admin' }));
    const dialogo = await screen.findByRole('dialog');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    expect(await within(dialogo).findByText('No puede darse de baja a sí mismo.')).toBeVisible();
  });

  it('reactivar: confirma el efecto y avisa', async () => {
    preparar();
    const reactivar = registrar('post', '/usuarios/12/reactivar', usuarioPersonal({ id: 12 }));
    const user = userEvent.setup();
    renderizarApp('/usuarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Reactivar a Pedro Baja' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Reactivar a Pedro Baja' });
    await user.click(within(dialogo).getByRole('button', { name: 'Reactivar' }));
    await waitFor(() => expect(reactivar).toHaveLength(1));
    expect(await screen.findByText('Usuario reactivado')).toBeInTheDocument();
  });

  it('reactivar con la sede en baja: explica que hay que reasignarlo primero', async () => {
    preparar();
    responder(
      'post',
      '/usuarios/12/reactivar',
      () => error(409, 'SEDE_EN_BAJA', 'La sede está dada de baja. Elija una sede activa.'),
      409,
    );
    const user = userEvent.setup();
    renderizarApp('/usuarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Reactivar a Pedro Baja' }));
    const dialogo = await screen.findByRole('dialog');
    await user.click(within(dialogo).getByRole('button', { name: 'Reactivar' }));
    expect(await within(dialogo).findByText(/Su sede está dada de baja/)).toBeVisible();
    expect(
      within(dialogo).getByRole('link', { name: 'asígnelo a una sede activa' }),
    ).toHaveAttribute('href', '/usuarios/12/editar');
  });

  it('un bibliotecario no accede a la pantalla ni la ve en el menú', async () => {
    sesionDe(BIBLIOTECARIO);
    renderizarApp('/usuarios', { conSesion: true });
    expect(await screen.findByText('No tiene permiso para ver esta pantalla.')).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument();
  });
});
