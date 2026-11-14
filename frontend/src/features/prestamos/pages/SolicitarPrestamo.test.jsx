import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  BIBLIOTECARIO,
  SOCIO,
  libro,
  pagina,
  prestamo,
  sedePublica,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const DISPONIBILIDAD = {
  libro_id: 12,
  titulo: 'Rayuela',
  total_red: { totales: 1, disponibles: 1 },
  por_sede: [],
};

const SEDES = [
  sedePublica({ id: 1, nombre: 'Sede Central' }),
  sedePublica({ id: 2, nombre: 'Sede Norte' }),
];

function propuesta(over = {}) {
  return {
    tipo: 'LOCAL',
    libro_id: 12,
    libro: 'Rayuela',
    sede_origen: { id: 1, nombre: 'Sede Central' },
    sede_destino: { id: 1, nombre: 'Sede Central' },
    plazo_dias: 14,
    retiro_hasta: '2026-11-13',
    ...over,
  };
}

function fichaDelLibro() {
  responder('get', '/libros/12', libro());
  responder('get', '/libros/12/disponibilidad', DISPONIBILIDAD);
  responder('get', '/sedes', pagina(SEDES));
}

async function abrirDialogo(user) {
  await user.click(await screen.findByRole('button', { name: 'Pedir préstamo' }));
  return screen.getByRole('dialog');
}

describe('Autogestión de préstamos', () => {
  it('CA-PRE-19: el socio pide un libro con disponibles en su sede y queda apartado', async () => {
    sesionDe(SOCIO);
    fichaDelLibro();
    const propuestas = registrar('get', '/prestamos/solicitudes/propuesta', propuesta());
    const solicitudes = registrar('post', '/prestamos/solicitudes', prestamo({ id: 120 }), 201);
    responder('get', '/prestamos/120', prestamo({ id: 120 }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/catalogo/12', { conSesion: true });

    const dialogo = await abrirDialogo(user);
    expect(
      await within(dialogo).findByText(/retiralo en el mostrador hasta el 13\/11\/2026/),
    ).toBeVisible();
    expect(within(dialogo).getByLabelText(/Lo retiro en/)).toHaveValue('1');
    expect(propuestas[0].url.searchParams.get('sede_destino_id')).toBeNull();
    expect(await axe(container)).toHaveNoViolations();
    await user.click(within(dialogo).getByRole('button', { name: 'Pedir préstamo' }));

    expect(await screen.findByText(/Préstamo P-2026-000118 solicitado/)).toBeVisible();
    expect(solicitudes[0].cuerpo).toEqual({
      libro_id: 12,
      sede_destino_id: 1,
      sede_origen_esperada_id: 1,
    });
  });

  it('CA-PRE-24: al cambiar la sede de retiro se recalcula la propuesta (entre sedes)', async () => {
    sesionDe(SOCIO);
    fichaDelLibro();
    const propuestas = registrar('get', '/prestamos/solicitudes/propuesta', ({ url }) =>
      url.searchParams.get('sede_destino_id') === '2'
        ? propuesta({
            tipo: 'INTERBIBLIOTECARIO',
            sede_destino: { id: 2, nombre: 'Sede Norte' },
            plazo_dias: 21,
            retiro_hasta: null,
          })
        : propuesta(),
    );
    const user = userEvent.setup();
    renderizarApp('/catalogo/12', { conSesion: true });

    const dialogo = await abrirDialogo(user);
    await within(dialogo).findByText(/retiralo en el mostrador/);
    await user.selectOptions(within(dialogo).getByLabelText(/Lo retiro en/), '2');

    expect(
      await within(dialogo).findByText(/sale de Sede Central y lo retirás en Sede Norte/),
    ).toBeVisible();
    expect(propuestas.at(-1).url.searchParams.get('sede_destino_id')).toBe('2');
  });

  it('CA-PRE-22: sin disponibles en la red ofrece reservar', async () => {
    sesionDe(SOCIO);
    fichaDelLibro();
    responder('get', '/prestamos/solicitudes/propuesta', () =>
      error(409, 'SIN_EJEMPLARES_DISPONIBLES', 'No hay ejemplares disponibles de este libro.', [
        { campo: 'libro_id', problema: 'sin_disponibles', sede_destino_id: 1 },
      ]),
    );
    const user = userEvent.setup();
    renderizarApp('/catalogo/12', { conSesion: true });

    const dialogo = await abrirDialogo(user);
    expect(await within(dialogo).findByText(/No hay ejemplares disponibles/)).toBeVisible();
    expect(within(dialogo).getByRole('button', { name: 'Pedir préstamo' })).toBeDisabled();
    await user.click(within(dialogo).getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByRole('dialog', { name: /Reservar «Rayuela»/ })).toBeVisible();
  });

  it('CA-PRE-28: si la disponibilidad cambió, avisa y muestra la nueva propuesta', async () => {
    sesionDe(SOCIO);
    fichaDelLibro();
    registrar('get', '/prestamos/solicitudes/propuesta', (_, llamadas) =>
      llamadas.length === 1
        ? propuesta()
        : propuesta({
            tipo: 'INTERBIBLIOTECARIO',
            sede_origen: { id: 2, nombre: 'Sede Norte' },
            retiro_hasta: null,
          }),
    );
    responder('post', '/prestamos/solicitudes', () =>
      error(409, 'DISPONIBILIDAD_CAMBIADA', 'La disponibilidad cambió.'),
    );
    const user = userEvent.setup();
    renderizarApp('/catalogo/12', { conSesion: true });

    const dialogo = await abrirDialogo(user);
    await within(dialogo).findByText(/retiralo en el mostrador/);
    await user.click(within(dialogo).getByRole('button', { name: 'Pedir préstamo' }));

    expect(await within(dialogo).findByText(/La disponibilidad cambió/)).toBeVisible();
    expect(await within(dialogo).findByText(/sale de Sede Norte/)).toBeVisible();
  });

  it('el bibliotecario no ve «Pedir préstamo» (registra en mostrador)', async () => {
    sesionDe(BIBLIOTECARIO);
    fichaDelLibro();
    responder('get', '/ejemplares', pagina([]));
    renderizarApp('/catalogo/12', { conSesion: true });

    await screen.findByRole('heading', { level: 1, name: 'Rayuela' });
    expect(screen.queryByRole('button', { name: 'Pedir préstamo' })).not.toBeInTheDocument();
  });

  it('CA-PRE-27, CA-PRE-29: el socio cancela su solicitud y no ve quién del personal la movió', async () => {
    sesionDe(SOCIO);
    const solicitado = prestamo({
      fecha_limite_retiro: '2026-11-13',
      historial: [
        {
          estado_anterior: null,
          estado_nuevo: 'SOLICITADO',
          fecha_hora: '2026-11-10T15:00:00Z',
          autor: 'Personal de la biblioteca',
          usuario: null,
          observacion: 'Solicitud registrada',
        },
      ],
    });
    delete solicitado.registrado_por;
    responder('get', '/prestamos/118', solicitado);
    const llamadas = registrar('post', '/prestamos/118/cancelar', {
      ...solicitado,
      estado: 'CANCELADO',
    });
    const user = userEvent.setup();
    renderizarApp('/prestamos/118', { conSesion: true });

    expect(await screen.findByText(/Podés retirarlo en .* hasta el 13\/11\/2026/)).toBeVisible();
    const historial = screen.getByRole('list', { name: 'Historial del préstamo' });
    expect(within(historial).getByText(/Personal de la biblioteca/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Cancelar solicitud' }));
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancelar solicitud' }),
    );

    await waitFor(() => expect(llamadas).toHaveLength(1));
    expect(llamadas[0].cuerpo).toEqual({ motivo: null });
  });
});
