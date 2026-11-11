import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { ADMIN, pagina, sedeAdmin, usuarioPersonal } from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const SEDES_ACTIVAS = pagina([
  sedeAdmin(),
  sedeAdmin({ id: 2, nombre: 'Sede Norte', codigo: 'NORTE' }),
]);

function preparar() {
  sesionDe(ADMIN);
  const sedes = registrar('get', '/sedes', SEDES_ACTIVAS);
  responder('get', '/usuarios', pagina([usuarioPersonal()]));
  return sedes;
}

async function completarBibliotecario(user) {
  await user.type(await screen.findByLabelText(/^Usuario/), 'nuevo.biblio');
  await user.type(screen.getByLabelText(/^Nombre/), 'Nora Nuevo');
  await user.selectOptions(screen.getByLabelText(/^Rol/), 'BIBLIOTECARIO');
  await user.selectOptions(screen.getByLabelText(/^Sede/), '2');
  await user.type(screen.getByLabelText(/^Contraseña/, { selector: 'input' }), 'Clave-segura-123');
  await user.type(screen.getByLabelText(/^Repetir contraseña/), 'Clave-segura-123');
}

describe('Alta de usuario', () => {
  it('crea un bibliotecario con su sede y vuelve al listado', async () => {
    const sedes = preparar();
    const alta = registrar('post', '/usuarios', usuarioPersonal({ id: 20 }), 201);
    const user = userEvent.setup();
    const { container } = renderizarApp('/usuarios/nuevo', { conSesion: true });

    await completarBibliotecario(user);
    // Para elegir sede solo se piden las activas.
    expect(sedes[0].url.searchParams.get('estado')).toBe('ACTIVA');
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));

    await waitFor(() => expect(alta).toHaveLength(1));
    // La confirmación de contraseña no se envía.
    expect(alta[0].cuerpo).toEqual({
      username: 'nuevo.biblio',
      password: 'Clave-segura-123',
      nombre: 'Nora Nuevo',
      rol: 'BIBLIOTECARIO',
      sede_id: 2,
    });
    expect(await screen.findByText('Usuario creado')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 1, name: 'Usuarios' })).toBeVisible();
  });

  it('un administrador no lleva sede: el campo desaparece y se envía sede_id nulo', async () => {
    preparar();
    const alta = registrar('post', '/usuarios', usuarioPersonal({ id: 21, rol: 'ADMIN' }), 201);
    const user = userEvent.setup();
    renderizarApp('/usuarios/nuevo', { conSesion: true });

    await user.type(await screen.findByLabelText(/^Usuario/), 'otro.admin');
    await user.type(screen.getByLabelText(/^Nombre/), 'Otro Admin');
    await user.selectOptions(screen.getByLabelText(/^Rol/), 'BIBLIOTECARIO');
    await user.selectOptions(screen.getByLabelText(/^Sede/), '1');
    await user.selectOptions(screen.getByLabelText(/^Rol/), 'ADMIN');
    expect(screen.queryByLabelText(/^Sede/)).not.toBeInTheDocument();
    await user.type(
      screen.getByLabelText(/^Contraseña/, { selector: 'input' }),
      'Clave-segura-123',
    );
    await user.type(screen.getByLabelText(/^Repetir contraseña/), 'Clave-segura-123');
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));

    await waitFor(() => expect(alta).toHaveLength(1));
    expect(alta[0].cuerpo).toMatchObject({ rol: 'ADMIN', sede_id: null });
  });

  it('valida antes de enviar: formato, contraseña, confirmación y sede', async () => {
    preparar();
    const alta = registrar('post', '/usuarios', usuarioPersonal(), 201);
    const user = userEvent.setup();
    renderizarApp('/usuarios/nuevo', { conSesion: true });

    await user.type(await screen.findByLabelText(/^Usuario/), 'a b');
    await user.type(
      screen.getByLabelText(/^Contraseña/, { selector: 'input' }),
      'solo-letras-largas',
    );
    await user.type(screen.getByLabelText(/^Repetir contraseña/), 'otra');
    await user.selectOptions(screen.getByLabelText(/^Rol/), 'BIBLIOTECARIO');
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));

    expect(await screen.findByText(/Use de 3 a 50 caracteres/)).toBeVisible();
    expect(screen.getByText('El nombre debe tener entre 3 y 100 caracteres')).toBeVisible();
    expect(
      screen.getByText('La contraseña debe incluir al menos una letra y un número'),
    ).toBeVisible();
    expect(screen.getByText('Las contraseñas no coinciden')).toBeVisible();
    expect(screen.getByText('Elija la sede del bibliotecario')).toBeVisible();
    expect(alta).toHaveLength(0);
  });

  it('usuario duplicado: el error queda junto al campo y se enfoca', async () => {
    preparar();
    registrar('post', '/usuarios', () => error(409, 'DUPLICADO', 'Duplicado'), 409);
    const user = userEvent.setup();
    renderizarApp('/usuarios/nuevo', { conSesion: true });

    await completarBibliotecario(user);
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));
    expect(await screen.findByText('Ya existe un usuario con ese nombre de usuario')).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText(/^Usuario/)).toHaveFocus());
  });

  it('sede en baja: muestra el mensaje del servidor junto a la sede', async () => {
    preparar();
    registrar(
      'post',
      '/usuarios',
      () => error(409, 'SEDE_EN_BAJA', 'La sede está dada de baja. Elija una sede activa.'),
      409,
    );
    const user = userEvent.setup();
    renderizarApp('/usuarios/nuevo', { conSesion: true });

    await completarBibliotecario(user);
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));
    expect(
      await screen.findByText('La sede está dada de baja. Elija una sede activa.'),
    ).toBeVisible();
  });

  it('errores de campo del servidor (contraseña) y error general', async () => {
    preparar();
    registrar(
      'post',
      '/usuarios',
      (_llamada, llamadas) =>
        llamadas.length === 1
          ? error(422, 'VALIDACION', 'Contraseña inválida', [
              { campo: 'password', problema: 'La contraseña es demasiado común.' },
            ])
          : error(500, 'ERROR_INTERNO', 'Falló el servidor'),
      422,
    );
    const user = userEvent.setup();
    renderizarApp('/usuarios/nuevo', { conSesion: true });

    await completarBibliotecario(user);
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));
    expect(await screen.findByText('La contraseña es demasiado común.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Falló el servidor');
  });
});

describe('Edición de usuario', () => {
  it('usuario y rol bloqueados, sede actual preseleccionada y aviso de vigencia', async () => {
    preparar();
    responder('get', '/usuarios/10', usuarioPersonal());
    const cambio = registrar('put', '/usuarios/10', usuarioPersonal({ sede_id: 2 }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/usuarios/10/editar', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Editar usuario' })).toBeVisible();
    // El formulario aparece cuando llegaron las sedes.
    expect(await screen.findByLabelText('Usuario')).toHaveValue('lucia.gomez');
    expect(screen.getByLabelText('Usuario')).toBeDisabled();
    expect(screen.getByLabelText('Rol')).toHaveValue('Bibliotecario');
    expect(screen.getByLabelText('Rol')).toBeDisabled();
    expect(screen.queryByLabelText(/^Contraseña/, { selector: 'input' })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Sede/)).toHaveValue('1');
    expect(screen.getByText(/rige desde la siguiente solicitud del usuario/)).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();

    await user.selectOptions(screen.getByLabelText(/^Sede/), '2');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(cambio).toHaveLength(1));
    expect(cambio[0].cuerpo).toEqual({ nombre: 'Lucía Gómez', sede_id: 2 });
    expect(await screen.findByText('Usuario guardado')).toBeInTheDocument();
  });

  it('administrador: solo el nombre, sin campo de sede', async () => {
    preparar();
    responder(
      'get',
      '/usuarios/11',
      usuarioPersonal({ id: 11, rol: 'ADMIN', sede_id: null, sede: null }),
    );
    const cambio = registrar('put', '/usuarios/11', usuarioPersonal({ id: 11 }));
    const user = userEvent.setup();
    renderizarApp('/usuarios/11/editar', { conSesion: true });

    const nombre = await screen.findByLabelText(/^Nombre/);
    expect(screen.queryByLabelText(/^Sede/)).not.toBeInTheDocument();
    await user.clear(nombre);
    await user.type(nombre, 'Ana Administradora');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(cambio).toHaveLength(1));
    expect(cambio[0].cuerpo).toEqual({ nombre: 'Ana Administradora', sede_id: null });
  });

  it('usuario dado de baja con la sede en baja: hay que elegir una sede activa', async () => {
    preparar();
    responder(
      'get',
      '/usuarios/12',
      usuarioPersonal({
        id: 12,
        activo: false,
        sede_id: 9,
        sede: { id: 9, codigo: 'VIEJA', nombre: 'Sede Vieja' },
      }),
    );
    const cambio = registrar('put', '/usuarios/12', usuarioPersonal({ id: 12 }));
    const user = userEvent.setup();
    renderizarApp('/usuarios/12/editar', { conSesion: true });

    expect(await screen.findByText(/está dado de baja. Puede reasignarlo/)).toBeVisible();
    expect(screen.getByText(/Su sede actual \(Sede Vieja\) está dada de baja/)).toBeVisible();
    expect(screen.getByLabelText(/^Sede/)).toHaveValue('');

    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Elija la sede del bibliotecario')).toBeVisible();
    expect(cambio).toHaveLength(0);

    await user.selectOptions(screen.getByLabelText(/^Sede/), '1');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(cambio).toHaveLength(1));
    expect(cambio[0].cuerpo.sede_id).toBe(1);
  });

  it('usuario inexistente: error sin reintento y vuelta al listado', async () => {
    preparar();
    responder('get', '/usuarios/99', () => error(404, 'USUARIO_NO_ENCONTRADO', 'No existe'), 404);
    renderizarApp('/usuarios/99/editar', { conSesion: true });

    expect(await screen.findByText('El usuario solicitado no existe')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver a usuarios' })).toHaveAttribute(
      'href',
      '/usuarios',
    );
  });
});
