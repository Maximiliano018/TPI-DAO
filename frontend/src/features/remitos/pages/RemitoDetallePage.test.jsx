import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { ADMIN, BIBLIOTECARIO, pagina, prestamo, remito } from '../../../../tests/datos.js';
import { registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const BIBLIO_NORTE = {
  ...BIBLIOTECARIO,
  id: 5,
  sede_id: 2,
  sede: { id: 2, codigo: 'NORTE', nombre: 'Sede Norte' },
};

describe('Remitos', () => {
  it('CA-REM-07: la ficha muestra el detalle y la trazabilidad; la sede origen empaqueta', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/remitos/51', remito());
    const llamadas = registrar('post', '/remitos/51/empaquetar', remito({ estado: 'EMPAQUETADO' }));
    const user = userEvent.setup();
    const { container } = renderizarApp('/remitos/51', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'R-2026-000051' })).toBeVisible();
    expect(screen.getByRole('list', { name: 'Movimientos del remito' })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Recibir' })).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await user.click(screen.getByRole('button', { name: 'Empaquetar' }));
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Empaquetar' }),
    );
    expect(await screen.findByText('Remito empaquetado')).toBeVisible();
    expect(llamadas).toHaveLength(1);
  });

  it('CA-REM-08: la sede destino no despacha, pero recibe y describe los daños', async () => {
    sesionDe(BIBLIO_NORTE);
    responder('get', '/remitos/51', remito({ estado: 'EN_TRANSITO' }));
    const llamadas = registrar('post', '/remitos/51/recibir', remito({ estado: 'DANADO' }));
    const user = userEvent.setup();
    renderizarApp('/remitos/51', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Recibir' }));
    expect(screen.queryByRole('button', { name: 'Despachar' })).not.toBeInTheDocument();
    const dialogo = screen.getByRole('dialog');
    await user.selectOptions(
      within(dialogo).getByLabelText(/Estado físico de CEN-000123/),
      'DANADO',
    );
    await user.type(within(dialogo).getByLabelText(/Qué le pasó a CEN-000123/), 'Tapa rota');
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar recepción' }));

    expect(await screen.findByText('Remito recibido')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({
      lineas: [
        {
          ejemplar_id: 301,
          estado_fisico: 'DANADO',
          destruido: false,
          faltante: false,
          observacion: 'Tapa rota',
        },
      ],
    });
  });

  it('CA-REM-23: un ejemplar que no llegó se marca faltante, sin estado físico', async () => {
    sesionDe(BIBLIO_NORTE);
    const dos = remito({
      estado: 'EN_TRANSITO',
      lineas: [
        ...remito().lineas,
        {
          ...remito().lineas[0],
          ejemplar_id: 302,
          codigo_ejemplar: 'CEN-000124',
          prestamo_id: 119,
        },
      ],
    });
    responder('get', '/remitos/51', dos);
    const llamadas = registrar('post', '/remitos/51/recibir', { ...dos, estado: 'INCOMPLETO' });
    const user = userEvent.setup();
    renderizarApp('/remitos/51', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Recibir' }));
    const dialogo = screen.getByRole('dialog');
    await user.click(within(dialogo).getByLabelText(/CEN-000124 no llegó/));
    expect(within(dialogo).getByLabelText(/Estado físico de CEN-000124/)).toBeDisabled();
    await user.type(
      within(dialogo).getByLabelText(/Qué le pasó a CEN-000124/),
      'No venía en la caja',
    );
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar recepción' }));

    expect(await screen.findByText('Remito recibido')).toBeVisible();
    expect(llamadas[0].cuerpo.lineas[1]).toEqual({
      ejemplar_id: 302,
      estado_fisico: null,
      destruido: false,
      faltante: true,
      observacion: 'No venía en la caja',
    });
  });

  it('CA-REM-22, CA-REM-25: muestra el atraso y el responsable de cada incidencia', async () => {
    sesionDe(ADMIN);
    responder(
      'get',
      '/remitos/51',
      remito({
        estado: 'INCOMPLETO',
        atrasado: true,
        lineas: [{ ...remito().lineas[0], resultado: 'FALTANTE' }],
        incidencias: [
          {
            id: 9,
            tipo: 'EXTRAVIO',
            origen: 'REMITO',
            ejemplar_id: 301,
            descripcion: 'No venía en la caja',
            fecha: '2026-11-12T15:00:00Z',
            usuario: { id: 5, nombre: 'Beto Norte' },
            sede_responsable: { id: 1, nombre: 'Sede Central' },
            despachado_por: { id: 2, nombre: 'Lucía Gómez' },
            resuelta_en: '2026-11-14T15:00:00Z',
            resolucion: 'Recuperado: apareció en el depósito',
          },
        ],
      }),
    );
    renderizarApp('/remitos/51', { conSesion: true });

    expect(
      await screen.findByText(/Atrasado: tenía que despacharse hasta el 13\/11\/2026/),
    ).toBeVisible();
    expect(screen.getByText(/Responsable: Sede Central \(despachó Lucía Gómez\)/)).toBeVisible();
    expect(screen.getByText(/Recuperado: apareció en el depósito/)).toBeVisible();
    const detalle = screen.getByRole('table', { name: 'Detalle del remito' });
    expect(within(detalle).getByText('No llegó')).toBeVisible();
  });

  it('el administrador puede marcar extraviado un envío en viaje', async () => {
    sesionDe(ADMIN);
    responder('get', '/remitos/51', remito({ estado: 'DESPACHADO' }));
    const llamadas = registrar('post', '/remitos/51/extraviado', remito({ estado: 'EXTRAVIADO' }));
    const user = userEvent.setup();
    renderizarApp('/remitos/51', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Marcar extraviado' }));
    const dialogo = screen.getByRole('dialog');
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'No llegó a destino');
    await user.click(within(dialogo).getByRole('button', { name: 'Marcar extraviado' }));

    expect(await screen.findByText('Remito marcado como extraviado')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ motivo: 'No llegó a destino' });
  });

  it('generar un envío con los préstamos que salen de la sede hacia un destino', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/prestamos',
      pagina([
        prestamo({
          tipo: 'INTERBIBLIOTECARIO',
          sede_destino_id: 2,
          sede_destino: 'Sede Norte',
        }),
        prestamo({ id: 200, numero: 'P-2026-000200', sede_origen_id: 2, sede_destino_id: 1 }),
      ]),
    );
    const llamadas = registrar('post', '/remitos', remito(), 201);
    responder('get', '/remitos/51', remito());
    const user = userEvent.setup();
    renderizarApp('/remitos/nuevo', { conSesion: true });

    await user.selectOptions(await screen.findByLabelText(/Sede destino/), '2');
    expect(screen.queryByText(/P-2026-000200/)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/P-2026-000118/));
    await user.click(screen.getByRole('button', { name: 'Generar remito (1)' }));

    expect(await screen.findByText('Remito R-2026-000051 generado')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({
      sede_destino_id: 2,
      motivo: 'ENVIO',
      lineas: [{ ejemplar_id: 301, prestamo_id: 118 }],
      observaciones: null,
    });
  });

  it('el administrador cambia un parámetro', async () => {
    sesionDe(ADMIN);
    responder('get', '/parametros', [
      { clave: 'plazo_prestamo_local_dias', valor: '14', descripcion: 'Plazo de préstamo local' },
    ]);
    const llamadas = registrar('put', '/parametros/plazo_prestamo_local_dias', {
      clave: 'plazo_prestamo_local_dias',
      valor: '10',
      descripcion: 'Plazo de préstamo local',
    });
    const user = userEvent.setup();
    renderizarApp('/parametros', { conSesion: true });

    const campo = await screen.findByLabelText('Plazo de préstamo local');
    await user.clear(campo);
    await user.type(campo, '10');
    await user.click(screen.getByRole('button', { name: 'Guardar Plazo de préstamo local' }));

    expect(await screen.findByText('Parámetro guardado')).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ valor: '10' });
  });
});
