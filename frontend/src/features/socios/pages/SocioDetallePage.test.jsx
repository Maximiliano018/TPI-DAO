import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  SOCIO,
  pagina,
  sedePublica,
  socio,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

describe('Ficha del socio', () => {
  it('muestra datos, situación y las acciones del bibliotecario', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/socios/45',
      socio({ situacion: { ...socio().situacion, prestamos_activos: 2, reservas_activas: 1 } }),
    );
    const { container } = renderizarApp('/socios/45', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Sol Socia' })).toBeVisible();
    expect(screen.getByText('DNI 30111222')).toBeInTheDocument();
    expect(within(screen.getByLabelText('Préstamos en curso')).getByText('2')).toBeVisible();
    expect(within(screen.getByLabelText('Reservas activas')).getByText('1')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Editar' })).toHaveAttribute(
      'href',
      '/socios/45/editar',
    );
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeVisible();
    // Inhabilitar es del administrador; la baja a pedido del socio la registra el personal.
    expect(screen.queryByRole('button', { name: 'Inhabilitar' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dar de baja' })).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('CA-SOC-10: el bibliotecario no ve «Rehabilitar» ante una inhabilitación administrativa', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/socios/45',
      socio({
        estado: 'INHABILITADO',
        motivo_inhabilitacion: 'ADMINISTRATIVA',
        causas_inhabilitacion: ['ADMINISTRATIVA'],
        motivo_administrativo: 'Daño reiterado',
      }),
    );
    renderizarApp('/socios/45', { conSesion: true });

    expect(await screen.findByText(/Causas: Decisión administrativa/)).toBeVisible();
    expect(screen.getByText(/Motivo administrativo: Daño reiterado/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Rehabilitar' })).not.toBeInTheDocument();
  });

  it('el administrador inhabilita con un motivo obligatorio', async () => {
    sesionDe(ADMIN);
    responder('get', '/socios/45', socio());
    const llamadas = registrar(
      'post',
      '/socios/45/inhabilitar',
      socio({ estado: 'INHABILITADO', motivo_inhabilitacion: 'ADMINISTRATIVA' }),
    );
    const user = userEvent.setup();
    renderizarApp('/socios/45', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Inhabilitar' }));
    const dialogo = screen.getByRole('dialog');
    await user.click(within(dialogo).getByRole('button', { name: 'Inhabilitar' }));
    expect(await within(dialogo).findByText(/entre 5 y 300 caracteres/)).toBeVisible();
    expect(llamadas).toHaveLength(0);

    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Daño reiterado de material');
    await user.click(within(dialogo).getByRole('button', { name: 'Inhabilitar' }));
    expect(await screen.findByText('Socio inhabilitado')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ motivo: 'Daño reiterado de material' });
  });

  it('la baja avisa que cancela las reservas activas e informa cuántas canceló', async () => {
    sesionDe(ADMIN);
    const conReservas = socio();
    conReservas.situacion.reservas_activas = 2;
    responder('get', '/socios/45', conReservas);
    responder('post', '/socios/45/baja', { ...socio({ estado: 'BAJA' }), reservas_canceladas: 2 });
    const user = userEvent.setup();
    renderizarApp('/socios/45', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    const dialogo = screen.getByRole('dialog');
    expect(dialogo).toHaveTextContent('Tiene 2 reservas activas: se van a cancelar');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Se mudó de ciudad');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    expect(await screen.findByText('Socio dado de baja. Se cancelaron 2 reservas.')).toBeVisible();
  });

  it('la baja bloqueada muestra el motivo que da el servidor', async () => {
    sesionDe(ADMIN);
    responder('get', '/socios/45', socio());
    responder('post', '/socios/45/baja', () =>
      error(409, 'SOCIO_CON_ACTIVIDAD_PENDIENTE', 'El socio 00045 tiene préstamos en curso.'),
    );
    const user = userEvent.setup();
    renderizarApp('/socios/45', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Se mudó de ciudad');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    expect(
      await within(dialogo).findByText('El socio 00045 tiene préstamos en curso.'),
    ).toBeVisible();
  });

  it('un socio dado de baja muestra el motivo y la opción de reactivar', async () => {
    sesionDe(ADMIN);
    responder(
      'get',
      '/socios/45',
      socio({
        estado: 'BAJA',
        tipo_baja: 'A_PEDIDO',
        reactivable: true,
        fecha_baja: '2026-11-01T12:00:00Z',
        motivo_baja: 'Se mudó',
      }),
    );
    renderizarApp('/socios/45', { conSesion: true });

    expect(await screen.findByText(/Motivo: Se mudó/)).toBeVisible();
    expect(screen.getByText(/A pedido del socio/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Reactivar' })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
  });

  it('crear la cuenta valida la clave y envía usuario y contraseña', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/socios/45', socio());
    const llamadas = registrar(
      'post',
      '/socios/45/cuenta',
      socio({ cuenta: { usuario_id: 9, username: 'sol.socia', activo: true } }),
      201,
    );
    const user = userEvent.setup();
    renderizarApp('/socios/45', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Crear cuenta' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Usuario/), 'sol.socia');
    await user.type(within(dialogo).getByLabelText(/^Contraseña/), 'Clave-segura-123');
    await user.type(within(dialogo).getByLabelText(/Repetir/), 'otra-clave-123');
    await user.click(within(dialogo).getByRole('button', { name: 'Crear cuenta' }));
    expect(await within(dialogo).findByText('Las contraseñas no coinciden')).toBeVisible();

    await user.clear(within(dialogo).getByLabelText(/Repetir/));
    await user.type(within(dialogo).getByLabelText(/Repetir/), 'Clave-segura-123');
    await user.click(within(dialogo).getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByText('Cuenta creada')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ username: 'sol.socia', password: 'Clave-segura-123' });
  });

  it('CA-SOC-11: el socio ve «Mis datos» sin acciones del personal', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([sedePublica()]));
    responder('get', '/socios/45', socio());
    const user = userEvent.setup();
    renderizarApp('/', { conSesion: true });

    await user.click(await screen.findByRole('link', { name: 'Mis datos' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Sol Socia' })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Crear cuenta' })).not.toBeInTheDocument();
    expect(screen.getByText(/pida la corrección en el mostrador/)).toBeVisible();
  });

  it('el bibliotecario solo registra la baja a pedido; el administrador elige el tipo', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/socios/45', socio());
    const user = userEvent.setup();
    const { unmount } = renderizarApp('/socios/45', { conSesion: true });
    await user.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    const tipo = within(screen.getByRole('dialog')).getByLabelText('Tipo de baja');
    expect(tipo).toBeDisabled();
    expect(
      within(tipo)
        .getAllByRole('option')
        .map((o) => o.value),
    ).toEqual(['A_PEDIDO']);
    unmount();

    sesionDe(ADMIN);
    const llamadas = registrar('post', '/socios/45/baja', {
      ...socio({ estado: 'BAJA' }),
      reservas_canceladas: 0,
    });
    renderizarApp('/socios/45', { conSesion: true });
    await user.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    const dialogo = screen.getByRole('dialog');
    await user.selectOptions(within(dialogo).getByLabelText('Tipo de baja'), 'FALLECIMIENTO');
    expect(dialogo).toHaveTextContent('Es definitiva');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Aviso de un familiar');
    await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
    await waitFor(() =>
      expect(llamadas[0].cuerpo).toEqual({ tipo: 'FALLECIMIENTO', motivo: 'Aviso de un familiar' }),
    );
  });

  it('con una solicitud pendiente el personal la aprueba o la rechaza según el tipo de baja', async () => {
    const enBaja = (tipo) =>
      socio({
        estado: 'BAJA',
        tipo_baja: tipo,
        reactivable: true,
        fecha_baja: '2026-11-01T12:00:00Z',
        motivo_baja: 'Se mudó',
        solicitud: { fecha: '2026-11-05T12:00:00Z', mensaje: 'Volví a la ciudad' },
      });
    sesionDe(BIBLIOTECARIO);
    responder('get', '/socios/45', enBaja('A_PEDIDO'));
    const llamadas = registrar('post', '/socios/45/solicitud-reactivacion/aprobar', socio());
    const user = userEvent.setup();
    const { unmount } = renderizarApp('/socios/45', { conSesion: true });

    expect(await screen.findByText(/Volví a la ciudad/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Rechazar solicitud' })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Reactivar' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Aprobar reactivación' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Aprobar' }));
    await waitFor(() => expect(llamadas).toHaveLength(1));
    unmount();

    // Una baja administrativa la resuelve solo el administrador.
    responder('get', '/socios/45', enBaja('ADMINISTRATIVA'));
    renderizarApp('/socios/45', { conSesion: true });
    await screen.findByText(/Volví a la ciudad/);
    expect(screen.queryByRole('button', { name: 'Aprobar reactivación' })).not.toBeInTheDocument();
  });

  it('el socio dado de baja pide la reactivación desde «Mis datos»', async () => {
    sesionDe(SOCIO);
    const propio = {
      ...socio({ estado: 'BAJA', tipo_baja: 'A_PEDIDO', reactivable: true }),
      fecha_baja: '2026-11-01T12:00:00Z',
      motivo_baja: 'Se mudó',
      cuenta: { username: 'sol.socia' },
    };
    delete propio.creado_por;
    responder('get', '/socios/45', propio);
    const llamadas = registrar('post', '/socios/45/solicitud-reactivacion', propio, 201);
    const user = userEvent.setup();
    renderizarApp('/mis-datos', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Solicitar la reactivación' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Mensaje/), 'Volví a la ciudad');
    await user.click(within(dialogo).getByRole('button', { name: 'Enviar solicitud' }));
    await waitFor(() => expect(llamadas[0]?.cuerpo).toEqual({ mensaje: 'Volví a la ciudad' }));
    expect(screen.queryByText('Auditoría')).not.toBeInTheDocument();
  });

  it('el historial muestra cada evento con su autor y su origen', async () => {
    sesionDe(SOCIO);
    responder('get', '/socios/45', socio());
    responder(
      'get',
      '/socios/45/historial',
      pagina([
        {
          id: 2,
          tipo_evento: 'CAMBIO_AUTOMATICO',
          fecha_hora: '2026-11-10T03:05:00Z',
          autor: 'Sistema',
          usuario: null,
          estado_anterior: 'HABILITADO',
          estado_nuevo: 'INHABILITADO',
          motivo: null,
          origen: 'Préstamo P-2026-0012 vencido',
          cambios: [{ campo: 'causas', antes: [], despues: ['PRESTAMO_VENCIDO'] }],
        },
      ]),
    );
    renderizarApp('/mis-datos?tab=historial', { conSesion: true });

    const linea = await screen.findByRole('list', { name: 'Historial del socio' });
    expect(linea).toHaveTextContent('Cambio automático de estado');
    expect(linea).toHaveTextContent(/Sistema ·/);
    expect(linea).toHaveTextContent('Origen: Préstamo P-2026-0012 vencido');
    expect(linea).toHaveTextContent('Causas: ninguna → Préstamo vencido');
  });
});
