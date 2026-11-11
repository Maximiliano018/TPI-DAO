import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { error, responder, sesionDe } from '../../../../tests/handlers.js';
import {
  ADMIN,
  BIBLIOTECARIO,
  SOCIO,
  pagina,
  sedeAdmin,
  sedeBasica,
  sedePublica,
} from '../../../../tests/datos.js';
import { renderizarApp } from '../../../../tests/render.jsx';

describe('Inicio por rol', () => {
  it('administrador: indicadores, accesos y sedes con «abierta ahora» y estado', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', { total: 4, activas: 3, en_baja: 1 });
    responder(
      'get',
      '/sedes',
      pagina([
        sedeAdmin(),
        sedeAdmin({ id: 2, codigo: 'NORTE', nombre: 'Sede Norte', abierta_ahora: false }),
        sedeAdmin({ id: 3, codigo: 'OESTE', nombre: 'Sede Oeste', estado: 'BAJA' }),
      ]),
    );
    renderizarApp('/', { conSesion: true });

    const activas = await screen.findByRole('region', { name: 'Sedes activas' });
    expect(await within(activas).findByText('3')).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: 'Sedes en baja' })).getByText('1'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: 'Total de sedes' })).getByText('4'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nueva sede' })).toHaveAttribute(
      'href',
      '/sedes/nueva',
    );

    const lista = await screen.findByRole('region', { name: 'Sedes de la red' });
    const filas = await within(lista).findAllByRole('listitem');
    expect(within(filas[0]).getByText('Abierta')).toBeInTheDocument();
    expect(within(filas[1]).getByText('Cerrada')).toBeInTheDocument();
    expect(within(filas[2]).getByText('Baja')).toBeInTheDocument();
    expect(within(filas[2]).queryByText('Abierta')).not.toBeInTheDocument();
  });

  it('administrador: si falla una tarjeta, las demás siguen funcionando', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/resumen', () => error(500, 'ERROR_INTERNO', 'Falló el resumen'));
    responder('get', '/sedes', pagina([sedeAdmin()]));
    renderizarApp('/', { conSesion: true });

    expect(await screen.findAllByRole('alert')).not.toHaveLength(0);
    expect(await screen.findByRole('link', { name: 'Sede Central' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Reintentar' }).length).toBeGreaterThan(0);
  });

  it('bibliotecario: su sede con horario de hoy y cierres próximos, y las demás sedes', async () => {
    sesionDe(BIBLIOTECARIO);
    responder(
      'get',
      '/sedes/1',
      sedeBasica({
        excepciones: [
          {
            id: 7,
            fecha: '2026-12-25',
            tipo: 'CIERRE_TOTAL',
            hora_desde: null,
            hora_hasta: null,
            motivo: 'Navidad',
          },
        ],
      }),
    );
    responder(
      'get',
      '/sedes',
      pagina([sedeBasica(), sedeBasica({ id: 2, codigo: 'NORTE', nombre: 'Sede Norte' })]),
    );
    renderizarApp('/', { conSesion: true });

    const miSede = await screen.findByRole('region', { name: 'Mi sede' });
    expect(await within(miSede).findByRole('link', { name: 'Sede Central' })).toHaveAttribute(
      'href',
      '/sedes/1',
    );
    expect(within(miSede).getByText(/Horario de hoy: 00:00–23:59/)).toBeInTheDocument();
    expect(within(miSede).getByText(/25\/12\/2026 \(todo el día\): Navidad/)).toBeInTheDocument();
    expect(within(miSede).getByText(/Responsable: Laura Pérez/)).toBeInTheDocument();
    const otras = await screen.findByRole('region', { name: 'Otras sedes de la red' });
    expect(await within(otras).findByRole('link', { name: 'Sede Norte' })).toBeInTheDocument();
    expect(within(otras).queryByRole('link', { name: 'Sede Central' })).not.toBeInTheDocument();
  });

  it('socio: sedes con abierta ahora, horario de hoy y contacto, sin datos de gestión', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([sedePublica()]));
    renderizarApp('/', { conSesion: true });

    const region = await screen.findByRole('region', {
      name: 'Sedes donde puede retirar y devolver',
    });
    expect(
      await within(region).findByText(/Hoy: 00:00–23:59 · \+543514221234/),
    ).toBeInTheDocument();
    expect(within(region).getByText('Abierta')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nueva sede' })).not.toBeInTheDocument();
    expect(screen.queryByText('Sedes activas')).not.toBeInTheDocument();
  });

  it('muestra el vacío cuando no hay sedes', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    renderizarApp('/', { conSesion: true });

    expect(await screen.findByText('No hay sedes para mostrar')).toBeInTheDocument();
  });
});
