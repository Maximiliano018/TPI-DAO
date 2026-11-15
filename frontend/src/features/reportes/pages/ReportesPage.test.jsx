import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADMIN, BIBLIOTECARIO, SOCIO, pagina } from '../../../../tests/datos.js';
import { registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const R1 = {
  desde: null,
  hasta: null,
  rutas: [
    {
      sede_origen_id: 1,
      sede_origen: 'Sede Central',
      sede_destino_id: 2,
      sede_destino: 'Sede Norte',
      envios: 2,
      ejemplares: 4,
      tiempo_promedio_transito_dias: 3,
    },
  ],
  total_envios: 2,
  total_ejemplares: 4,
};

const fila = (libroId, titulo) => ({
  libro_id: libroId,
  titulo,
  sede_id: 1,
  sede: 'Sede Central',
  totales: 1,
  disponibles: 1,
  prestados: 0,
  reservados: 0,
  en_transito: 0,
  otros: 0,
});

/** Texto de un Blob de jsdom (no implementa `blob.text()`). */
const leer = (blob) =>
  new Promise((resolver) => {
    const lector = new FileReader();
    lector.onload = () => resolver(lector.result);
    lector.readAsText(blob);
  });

const pestanas = () => screen.getAllByRole('tab').map((t) => t.textContent);

describe('Reportes', () => {
  it('CA-REP-01: el administrador ve todos los reportes y el tránsito promedio por ruta', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes', pagina([]));
    responder('get', '/reportes/movimiento-entre-sedes', R1);
    const user = userEvent.setup();
    const { container } = renderizarApp('/', { conSesion: true });

    await user.click(await screen.findByRole('link', { name: 'Reportes' }));
    const tabla = await screen.findByRole('table', { name: 'Rutas entre sedes' });

    expect(pestanas()).toEqual([
      'Movimiento entre sedes',
      'Envíos e incidencias',
      'Libros más pedidos',
      'Vencidos y multas',
      'Disponibilidad',
      'Activos y en tránsito',
    ]);
    expect(within(tabla).getByText('Sede Norte')).toBeVisible();
    expect(within(tabla).getByText('3')).toBeVisible();
    expect(screen.getByRole('region', { name: 'Envíos recibidos' })).toHaveTextContent('2');
    expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeEnabled();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('CA-REP-12: el bibliotecario no ve R2 ni R3 y no elige sede', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/sedes', pagina([]));
    responder('get', '/reportes/movimiento-entre-sedes', { ...R1, rutas: [], total_envios: 0 });
    renderizarApp('/reportes', { conSesion: true });

    expect(await screen.findByText('Sin resultados')).toBeVisible();
    expect(pestanas()).toEqual([
      'Movimiento entre sedes',
      'Vencidos y multas',
      'Disponibilidad',
      'Activos y en tránsito',
    ]);
    expect(screen.queryByLabelText('Sede')).not.toBeInTheDocument();
    expect(screen.getByText(/datos registrados de Sede Central/)).toBeVisible();
  });

  it('CA-REP-14: un rango con fin anterior al inicio no se emite', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes', pagina([]));
    const llamadas = registrar('get', '/reportes/movimiento-entre-sedes', R1);
    renderizarApp('/reportes?desde=2026-11-10&hasta=2026-11-01', { conSesion: true });

    expect(await screen.findByText(/no puede ser anterior/)).toBeVisible();
    expect(llamadas).toHaveLength(0);
  });

  it('CA-REP-08: R4 muestra los vencidos con su multa acumulada y el total adeudado', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/reportes/vencidos-y-multas', {
      fecha: '2026-11-12',
      monto_por_dia: '200.00',
      vencidos: [
        {
          prestamo_id: 118,
          numero: 'P-2026-000118',
          socio_id: 45,
          socio: 'Sol Socia',
          numero_socio: '00045',
          libro: 'Rayuela',
          sede: 'Sede Central',
          sede_origen: 'Sede Central',
          fecha_vencimiento: '2026-11-08',
          dias_atraso: 4,
          multa_acumulada: '800.00',
        },
      ],
      multas: [],
      cantidad_vencidos: 1,
      total_acumulado_vencidos: '800.00',
      total_multas_pendientes: '0.00',
      total_adeudado: '800.00',
    });
    renderizarApp('/reportes?r=r4', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Préstamos vencidos' });
    expect(within(tabla).getByText('4')).toBeVisible();
    expect(screen.getByRole('region', { name: 'Total adeudado' })).toHaveTextContent(/800,00/);
  });

  it('CA-REP-10: el socio solo emite la disponibilidad por sede', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes', pagina([]));
    responder('get', '/categorias', []);
    responder('get', '/reportes/disponibilidad-por-sede', {
      items: [
        {
          libro_id: 12,
          titulo: 'Rayuela',
          sede_id: 1,
          sede: 'Sede Central',
          totales: 2,
          disponibles: 1,
          prestados: 1,
          reservados: 0,
          en_transito: 0,
          otros: 0,
        },
      ],
      total: 1,
      page: 1,
      size: 50,
    });
    renderizarApp('/reportes?r=r2', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Disponibilidad por sede' });
    expect(pestanas()).toEqual(['Disponibilidad']);
    expect(within(tabla).getByText('Rayuela')).toBeVisible();
  });

  describe('filtros y exportación', () => {
    afterEach(() => {
      vi.restoreAllMocks();
      delete URL.createObjectURL;
      delete URL.revokeObjectURL;
    });

    it('CA-REP-22: el CSV de R5 trae todas las páginas y no ejecuta fórmulas', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes', pagina([]));
      responder('get', '/categorias', []);
      const llamadas = registrar('get', '/reportes/disponibilidad-por-sede', ({ url }) =>
        url.searchParams.get('size') === '200'
          ? {
              items: [fila(1, 'Rayuela'), fila(2, '=HYPERLINK("x")'), fila(3, 'Ficciones')],
              total: 3,
              page: 1,
              size: 200,
            }
          : { items: [fila(1, 'Rayuela')], total: 3, page: 1, size: 1 },
      );
      const blobs = [];
      // jsdom no implementa los objetos URL: se reemplazan para capturar el archivo.
      URL.createObjectURL = vi.fn((blob) => {
        blobs.push(blob);
        return 'blob:csv';
      });
      URL.revokeObjectURL = vi.fn();
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      const user = userEvent.setup();
      renderizarApp('/reportes?r=r5&categoria_id=4', { conSesion: true });

      await screen.findByRole('table', { name: 'Disponibilidad por sede' });
      await user.click(screen.getByRole('button', { name: 'Exportar CSV' }));

      await vi.waitFor(() => expect(blobs).toHaveLength(1));
      const exportacion = llamadas.at(-1).url.searchParams;
      expect([exportacion.get('page'), exportacion.get('categoria_id')]).toEqual(['1', '4']);
      const lineas = (await leer(blobs[0])).replace('\ufeff', '').split('\r\n');
      expect(lineas).toHaveLength(4);
      expect(lineas[2]).toMatch(/^"'=HYPERLINK\(""x""\)";/);
    });

    it('CA-REP-16: R4 filtra por atraso y no consulta con un rango de atraso invertido', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes', pagina([]));
      const llamadas = registrar('get', '/reportes/vencidos-y-multas', {
        fecha: '2026-11-12',
        monto_por_dia: '200.00',
        vencidos: [],
        multas: [],
        cantidad_vencidos: 3,
        total_acumulado_vencidos: '1400.00',
        total_multas_pendientes: '0.00',
        total_adeudado: '1400.00',
      });
      renderizarApp('/reportes?r=r4&atraso_min=5&atraso_max=2', { conSesion: true });

      expect(await screen.findByText(/no puede ser menor/)).toBeVisible();
      expect(llamadas).toHaveLength(0);
      await userEvent.setup().clear(screen.getByLabelText('Atraso hasta (días)'));

      await vi.waitFor(() => expect(llamadas).toHaveLength(1));
      expect(llamadas[0].url.searchParams.get('atraso_min')).toBe('5');
      // Los totales son los del alcance, aunque la lista filtrada quede vacía.
      expect(await screen.findByRole('region', { name: 'Préstamos vencidos' })).toHaveTextContent(
        '3',
      );
    });

    it('CA-REP-16: R6 filtra por estado, tipo de préstamo y estado del remito', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes', pagina([]));
      const llamadas = registrar('get', '/reportes/prestamos-activos-y-en-transito', {
        fecha: '2026-11-12',
        prestamos: [],
        remitos: [],
      });
      const user = userEvent.setup();
      renderizarApp('/reportes?r=r6', { conSesion: true });

      await screen.findByText('Sin resultados');
      await user.selectOptions(screen.getByLabelText('Préstamos'), 'VENCIDO');
      await user.selectOptions(screen.getByLabelText('Tipo de préstamo'), 'LOCAL');
      await user.selectOptions(screen.getByLabelText('Estado del remito'), 'DESPACHADO');

      await vi.waitFor(() =>
        expect(Object.fromEntries(llamadas.at(-1).url.searchParams)).toEqual({
          estado: 'VENCIDO',
          tipo: 'LOCAL',
          estado_remito: 'DESPACHADO',
        }),
      );
    });
  });
});
