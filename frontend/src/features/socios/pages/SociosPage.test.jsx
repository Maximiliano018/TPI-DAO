import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { BIBLIOTECARIO, SOCIO, pagina, socio } from '../../../../tests/datos.js';
import { registrar, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const SOCIOS = [
  socio(),
  socio({
    id: 46,
    numero_socio: '00046',
    nombre: 'Juan',
    apellido: 'Álvarez',
    estado: 'INHABILITADO',
    motivo_inhabilitacion: 'PRESTAMO_VENCIDO',
  }),
  socio({ id: 47, numero_socio: '00047', nombre: 'Diego', apellido: 'Luna', estado: 'BAJA' }),
];

describe('Listado de socios', () => {
  it('muestra número, nombre con enlace a la ficha, documento y estado con su causa', async () => {
    sesionDe(BIBLIOTECARIO);
    registrar('get', '/socios', pagina(SOCIOS));
    const { container } = renderizarApp('/socios', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Socios' });
    const filas = within(tabla).getAllByRole('row').slice(1);
    expect(filas).toHaveLength(3);
    expect(within(filas[0]).getByText('00045')).toBeInTheDocument();
    expect(within(filas[0]).getByRole('link', { name: 'Socia, Sol' })).toHaveAttribute(
      'href',
      '/socios/45',
    );
    expect(within(filas[0]).getByText('DNI 30111222')).toBeInTheDocument();
    expect(within(filas[0]).getByText('Habilitado')).toBeInTheDocument();
    expect(within(filas[1]).getByText('Inhabilitado · Préstamo vencido')).toBeInTheDocument();
    expect(within(filas[2]).getByText('Dado de baja')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nuevo socio' })).toHaveAttribute(
      'href',
      '/socios/nuevo',
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('la búsqueda y el estado viajan a la API', async () => {
    sesionDe(BIBLIOTECARIO);
    const llamadas = registrar('get', '/socios', pagina(SOCIOS));
    const user = userEvent.setup();
    renderizarApp('/socios?q=gomez', { conSesion: true });

    await screen.findByRole('table', { name: 'Socios' });
    expect(llamadas[0].url.searchParams.get('q')).toBe('gomez');
    await user.selectOptions(screen.getByLabelText('Estado'), 'INHABILITADO');
    await waitFor(() =>
      expect(llamadas.at(-1).url.searchParams.get('estado')).toBe('INHABILITADO'),
    );
  });

  it('filtra las solicitudes de reactivación pendientes y las marca en la tabla', async () => {
    sesionDe(BIBLIOTECARIO);
    const llamadas = registrar(
      'get',
      '/socios',
      pagina([{ ...SOCIOS[0], estado: 'BAJA', solicitud_pendiente: true }]),
    );
    const user = userEvent.setup();
    renderizarApp('/socios', { conSesion: true });

    await screen.findByRole('table', { name: 'Socios' });
    expect(screen.getByText('Pide reactivación')).toBeVisible();
    await user.selectOptions(screen.getByLabelText('Reactivación'), 'true');
    await waitFor(() =>
      expect(llamadas.at(-1).url.searchParams.get('solicitud_pendiente')).toBe('true'),
    );
  });

  it('sin resultados ofrece limpiar los filtros', async () => {
    sesionDe(BIBLIOTECARIO);
    registrar('get', '/socios', pagina([]));
    renderizarApp('/socios?q=nadie', { conSesion: true });

    expect(await screen.findByText('No hay socios que coincidan')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Limpiar filtros' }).length).toBeGreaterThan(0);
  });

  it('un socio no entra al listado', async () => {
    sesionDe(SOCIO);
    renderizarApp('/socios', { conSesion: true });

    expect(await screen.findByText('No tiene permiso para ver esta pantalla.')).toBeVisible();
  });
});
