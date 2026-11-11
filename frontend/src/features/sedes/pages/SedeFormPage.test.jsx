import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { ADMIN, BIBLIOTECARIO, LOCALIDADES, sedeAdmin } from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

async function completarAlta(user) {
  await user.type(await screen.findByLabelText(/^Código/), 'norte');
  await user.type(screen.getByLabelText(/^Nombre/), 'Sede Norte');
  await user.type(screen.getByLabelText(/^Calle/), 'Av. Colón');
  await user.type(screen.getByLabelText(/^Número/), '4500');
  await user.click(screen.getByRole('combobox', { name: 'Localidad' }));
  await user.click(await screen.findByRole('option', { name: /Villa María/ }));
  await user.type(screen.getByLabelText(/^Teléfono/), '+54 351 400-0000');
  await user.type(screen.getByLabelText(/^Correo/), 'norte@red.example');
  await user.type(screen.getByLabelText(/^Responsable/), 'Ana Pérez');
  await user.click(screen.getByRole('button', { name: 'Agregar franja el Lunes' }));
}

const CUERPO_ALTA = {
  codigo: 'NORTE',
  nombre: 'Sede Norte',
  calle: 'Av. Colón',
  numero: '4500',
  localidad_id: 2,
  telefono: '+54 351 400-0000',
  email: 'norte@red.example',
  responsable: 'Ana Pérez',
  horarios: [{ dia_semana: 1, apertura: '09:00', cierre: '13:00' }],
  confirmar_direccion_duplicada: false,
};

function preparar(usuario = ADMIN) {
  sesionDe(usuario);
  responder('get', '/localidades', LOCALIDADES);
}

describe('Alta de sede', () => {
  it('completa y envía el formulario; vuelve al detalle con aviso', async () => {
    preparar();
    const alta = registrar('post', '/sedes', sedeAdmin({ id: 10, codigo: 'NORTE' }), 201);
    responder('get', '/sedes/10', sedeAdmin({ id: 10, codigo: 'NORTE', nombre: 'Sede Norte' }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/sedes/nueva', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Nueva sede' })).toBeVisible();
    await completarAlta(user);
    // La provincia sale de la localidad y no se edita.
    expect(screen.getByLabelText('Provincia')).toHaveValue('Córdoba');
    expect(screen.getByLabelText(/^Código/)).toHaveValue('NORTE');
    expect(await axe(container)).toHaveNoViolations();

    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    await waitFor(() => expect(alta).toHaveLength(1));
    expect(alta[0].cuerpo).toEqual(CUERPO_ALTA);
    expect(await screen.findByText('Sede guardada')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 1, name: 'Sede Norte' })).toBeVisible();
  });

  it('valida antes de enviar y enfoca los problemas', async () => {
    preparar();
    const alta = registrar('post', '/sedes', sedeAdmin(), 201);
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Guardar sede' }));
    expect(
      await screen.findByText(/El código debe tener de 3 a 15 caracteres/),
    ).toBeInTheDocument();
    expect(screen.getByText('El nombre debe tener entre 3 y 100 caracteres')).toBeInTheDocument();
    expect(screen.getByText('Elija una localidad de la lista')).toBeInTheDocument();
    expect(screen.getByText('Cargue al menos una franja horaria.')).toBeInTheDocument();
    expect(alta).toHaveLength(0);
  });

  it('valida formato de teléfono, correo y número de puerta', async () => {
    preparar();
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await user.type(await screen.findByLabelText(/^Número/), '12 B');
    await user.type(screen.getByLabelText(/^Teléfono/), '4221234');
    await user.type(screen.getByLabelText(/^Correo/), 'sin-arroba');
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    expect(await screen.findByText('Use el número de puerta (1250, 1250B) o S/N')).toBeVisible();
    expect(screen.getByText(/Use el formato internacional/)).toBeVisible();
    expect(screen.getByText('El correo electrónico no tiene un formato válido')).toBeVisible();
  });

  it('marca franjas solapadas y no envía', async () => {
    preparar();
    const alta = registrar('post', '/sedes', sedeAdmin(), 201);
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await completarAlta(user);
    await user.click(screen.getByRole('button', { name: 'Agregar franja el Lunes' }));
    fireEvent.change(screen.getByLabelText('Lunes, franja 2: apertura'), {
      target: { value: '12:00' },
    });
    fireEvent.change(screen.getByLabelText('Lunes, franja 2: cierre'), {
      target: { value: '15:00' },
    });
    expect(screen.getByText('Las franjas 1 y 2 se solapan.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    expect(alta).toHaveLength(0);
  });

  it('dirección duplicada: permite corregir o guardar de todas formas', async () => {
    preparar();
    const alta = registrar(
      'post',
      '/sedes',
      ({ cuerpo }) =>
        cuerpo.confirmar_direccion_duplicada
          ? sedeAdmin({ id: 10 })
          : error(409, 'DIRECCION_DUPLICADA', 'Ya existe una sede en esa dirección', [
              {
                campo: 'direccion',
                problema: 'duplicada',
                sede: { id: 1, codigo: 'CEN', nombre: 'Sede Central', estado: 'ACTIVA' },
              },
            ]),
      201,
    );
    responder('get', '/sedes/10', sedeAdmin({ id: 10 }));
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await completarAlta(user);
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Ya hay una sede en esa dirección' });
    expect(within(dialogo).getByRole('link', { name: 'Sede Central' })).toHaveAttribute(
      'href',
      '/sedes/1',
    );

    // «Volver y corregir» deja el formulario con sus datos.
    await user.click(within(dialogo).getByRole('button', { name: 'Volver y corregir' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Calle/)).toHaveValue('Av. Colón');

    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    await user.click(await screen.findByRole('button', { name: 'Guardar de todas formas' }));
    await waitFor(() => expect(alta).toHaveLength(3));
    expect(alta[1].cuerpo.confirmar_direccion_duplicada).toBe(false);
    expect(alta[2].cuerpo).toEqual({ ...CUERPO_ALTA, confirmar_direccion_duplicada: true });
    expect(await screen.findByText('Sede guardada')).toBeInTheDocument();
  });

  it('errores de campo del servidor se muestran junto al campo', async () => {
    preparar();
    registrar(
      'post',
      '/sedes',
      () =>
        error(422, 'VALIDACION', 'Dato inválido', [
          { campo: 'telefono', problema: 'El teléfono ya está en uso por otra sede' },
        ]),
      422,
    );
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await completarAlta(user);
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    expect(await screen.findByText('El teléfono ya está en uso por otra sede')).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText(/^Teléfono/)).toHaveFocus());
  });

  it('código duplicado: se marca en el campo código', async () => {
    preparar();
    registrar('post', '/sedes', () => error(409, 'SEDE_CODIGO_DUPLICADO', 'Código repetido'), 409);
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await completarAlta(user);
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    expect(await screen.findByText('Ya existe una sede con ese código')).toBeVisible();
  });

  it('un error sin campo va en un aviso arriba', async () => {
    preparar();
    registrar('post', '/sedes', () => error(500, 'ERROR_INTERNO', 'Falló el servidor'), 500);
    const user = userEvent.setup();
    renderizarApp('/sedes/nueva', { conSesion: true });

    await completarAlta(user);
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Falló el servidor');
  });

  it('un bibliotecario no accede al alta', async () => {
    preparar(BIBLIOTECARIO);
    renderizarApp('/sedes/nueva', { conSesion: true });
    expect(await screen.findByText('No tiene permiso para ver esta pantalla.')).toBeVisible();
  });
});

describe('Edición de sede', () => {
  const completa = () =>
    sedeAdmin({
      version: 3,
      horarios: [{ dia_semana: 2, apertura: '08:00', cierre: '12:00' }],
    });

  it('precarga los datos, bloquea el código y envía la versión leída', async () => {
    preparar();
    responder('get', '/sedes/1', completa());
    const cambio = registrar('put', '/sedes/1', sedeAdmin());
    const user = userEvent.setup();
    const { container } = renderizarApp('/sedes/1/editar', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Editar sede' })).toBeVisible();
    const codigo = screen.getByLabelText(/^Código/);
    expect(codigo).toHaveValue('CEN');
    expect(codigo).toBeDisabled();
    expect(screen.getByText('El código no se puede cambiar')).toBeVisible();
    expect(screen.getByLabelText(/^Calle/)).toHaveValue('Av. Colón');
    // El catálogo de localidades llega aparte: el campo se completa al recibirlo.
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Localidad' })).toHaveValue('Córdoba'),
    );
    expect(screen.getByLabelText('Provincia')).toHaveValue('Córdoba');
    expect(screen.getByLabelText('Martes, franja 1: apertura')).toHaveValue('08:00');
    expect(await axe(container)).toHaveNoViolations();

    const nombre = screen.getByLabelText(/^Nombre/);
    await user.clear(nombre);
    await user.type(nombre, 'Sede Central Renovada');
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));

    await waitFor(() => expect(cambio).toHaveLength(1));
    expect(cambio[0].cuerpo).toMatchObject({
      codigo: 'CEN',
      nombre: 'Sede Central Renovada',
      version: 3,
      localidad_id: 1,
      horarios: [{ dia_semana: 2, apertura: '08:00', cierre: '12:00' }],
      confirmar_direccion_duplicada: false,
    });
  });

  it('conflicto de versión: diálogo con «Recargar» que trae los datos vigentes', async () => {
    preparar();
    registrar('get', '/sedes/1', (_llamada, llamadas) =>
      llamadas.length === 1
        ? completa()
        : sedeAdmin({ version: 4, nombre: 'Nombre de otra persona' }),
    );
    const cambio = registrar('put', '/sedes/1', (_llamada, llamadas) =>
      llamadas.length === 1
        ? error(409, 'CONFLICTO_DE_VERSION', 'Otra persona modificó la sede')
        : sedeAdmin({ version: 5 }),
    );
    const user = userEvent.setup();
    renderizarApp('/sedes/1/editar', { conSesion: true });

    const nombre = await screen.findByLabelText(/^Nombre/);
    await user.clear(nombre);
    await user.type(nombre, 'Mi cambio');
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));

    const dialogo = await screen.findByRole('dialog', { name: 'Otra persona modificó esta sede' });
    await user.click(within(dialogo).getByRole('button', { name: 'Recargar' }));
    await waitFor(() =>
      expect(screen.getByLabelText(/^Nombre/)).toHaveValue('Nombre de otra persona'),
    );

    // Tras recargar, el siguiente guardado usa la versión nueva.
    await user.click(screen.getByRole('button', { name: 'Guardar sede' }));
    await waitFor(() => expect(cambio).toHaveLength(2));
    expect(cambio[0].cuerpo.version).toBe(3);
    expect(cambio[1].cuerpo.version).toBe(4);
  });

  it('una sede en baja redirige al detalle con aviso', async () => {
    preparar();
    responder('get', '/sedes/1', sedeAdmin({ estado: 'BAJA' }));
    renderizarApp('/sedes/1/editar', { conSesion: true });

    expect(await screen.findByText('Reactive la sede para poder editarla')).toBeVisible();
    expect(screen.getByRole('heading', { level: 1, name: 'Sede Central' })).toBeVisible();
  });

  it('una sede inexistente muestra el error sin reintento', async () => {
    preparar();
    responder('get', '/sedes/99', () => error(404, 'SEDE_NO_ENCONTRADA', 'No existe'), 404);
    renderizarApp('/sedes/99/editar', { conSesion: true });

    expect(
      await screen.findByText('La sede solicitada no existe o no está disponible'),
    ).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
  });
});
