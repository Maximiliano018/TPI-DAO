import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { ADMIN, BIBLIOTECARIO, pagina, sedeAdmin, socio } from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

async function completar(user, { documento = '30.111.222' } = {}) {
  await user.type(await screen.findByLabelText(/Número de documento/), documento);
  await user.type(screen.getByLabelText(/^Nombre/), 'Sol');
  await user.type(screen.getByLabelText(/^Apellido/), 'Socia');
  await user.type(screen.getByLabelText(/Fecha de nacimiento/), '1995-04-12');
  await user.type(screen.getByLabelText(/Correo/), 'sol@example.com');
}

function preparar(usuario = BIBLIOTECARIO) {
  sesionDe(usuario);
  responder('get', '/sedes', pagina([sedeAdmin(), sedeAdmin({ id: 2, nombre: 'Sede Norte' })]));
  responder('get', '/socios/45', socio());
}

describe('Alta y edición de socios', () => {
  it('CA-SOC-01: el bibliotecario registra en su sede y va a la ficha', async () => {
    preparar();
    const llamadas = registrar('post', '/socios', socio(), 201);
    const user = userEvent.setup();
    const { container } = renderizarApp('/socios/nuevo', { conSesion: true });

    await completar(user);
    expect(screen.getByText(/Se registra en su sede \(Sede Central\)/)).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole('button', { name: 'Registrar socio' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Sol Socia' })).toBeVisible();
    expect(llamadas[0].cuerpo).toMatchObject({
      tipo_documento: 'DNI',
      nro_documento: '30.111.222',
      nombre: 'Sol',
      apellido: 'Socia',
      fecha_nacimiento: '1995-04-12',
      email: 'sol@example.com',
      telefono: null,
      sede_alta_id: null,
      confirmar_posible_duplicado: false,
    });
  });

  it('exige al menos un medio de contacto y el administrador elige la sede', async () => {
    preparar(ADMIN);
    const llamadas = registrar('post', '/socios', socio(), 201);
    const user = userEvent.setup();
    renderizarApp('/socios/nuevo', { conSesion: true });

    await user.type(await screen.findByLabelText(/Número de documento/), '30111222');
    await user.type(screen.getByLabelText(/^Nombre/), 'Sol');
    await user.type(screen.getByLabelText(/^Apellido/), 'Socia');
    await user.click(screen.getByRole('button', { name: 'Registrar socio' }));
    expect(
      await screen.findByText('Indique al menos un correo o un teléfono de contacto'),
    ).toBeVisible();
    expect(llamadas).toHaveLength(0);

    await user.type(screen.getByLabelText(/Teléfono/), '+543515000000');
    await user.selectOptions(screen.getByRole('combobox', { name: /^Sede/ }), '2');
    await user.click(screen.getByRole('button', { name: 'Registrar socio' }));
    await screen.findByRole('heading', { level: 1, name: 'Sol Socia' });
    expect(llamadas[0].cuerpo.sede_alta_id).toBe(2);
  });

  it('CA-SOC-03: un documento repetido enlaza al socio existente', async () => {
    preparar();
    responder('post', '/socios', () =>
      error(409, 'DUPLICADO', 'Ya existe el socio 00045. Está dado de baja: puede reactivarse.', [
        { campo: 'nro_documento', socio_id: 45, numero_socio: '00045', puede_reactivarse: true },
      ]),
    );
    const user = userEvent.setup();
    renderizarApp('/socios/nuevo', { conSesion: true });

    await completar(user);
    await user.click(screen.getByRole('button', { name: 'Registrar socio' }));

    expect(await screen.findByText(/puede reactivarse/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Ver la ficha del socio 00045' })).toHaveAttribute(
      'href',
      '/socios/45',
    );
  });

  it('un posible duplicado se registra solo si se confirma que es otra persona', async () => {
    preparar();
    const llamadas = registrar('post', '/socios', (_llamada, todas) =>
      todas.length === 1
        ? error(409, 'POSIBLE_DUPLICADO', 'Hay socios parecidos.', [
            { campo: 'nombre', socio_id: 12, numero_socio: '00012', nombre: 'Sol Socia' },
          ])
        : socio(),
    );
    const user = userEvent.setup();
    renderizarApp('/socios/nuevo', { conSesion: true });

    await completar(user, { documento: '40111222' });
    await user.click(screen.getByRole('button', { name: 'Registrar socio' }));
    const aviso = await screen.findByText(/Revise que no sea la misma persona/);
    expect(within(aviso.closest('[role="alert"], div')).getByRole('link')).toHaveAttribute(
      'href',
      '/socios/12',
    );

    await user.click(screen.getByRole('button', { name: 'Es otra persona: registrar igual' }));
    await screen.findByRole('heading', { level: 1, name: 'Sol Socia' });
    expect(llamadas.map((l) => l.cuerpo.confirmar_posible_duplicado)).toEqual([false, true]);
  });

  it('la edición precarga los datos y guarda con PUT', async () => {
    preparar();
    const llamadas = registrar('put', '/socios/45', socio({ apellido: 'Pérez' }));
    const user = userEvent.setup();
    renderizarApp('/socios/45/editar', { conSesion: true });

    const apellido = await screen.findByLabelText(/^Apellido/);
    expect(apellido).toHaveValue('Socia');
    expect(screen.queryByText(/Sede de alta/)).not.toBeInTheDocument();
    await user.clear(apellido);
    await user.type(apellido, 'Pérez');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));

    expect(await screen.findByText('Socio guardado')).toBeVisible();
    expect(llamadas[0].cuerpo).toMatchObject({ apellido: 'Pérez', nro_documento: '30111222' });
    expect(llamadas[0].cuerpo).not.toHaveProperty('sede_alta_id');
  });
});
