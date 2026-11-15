import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { SOCIO, multa, pago, pagina } from '../../../../tests/datos.js';
import { registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';
import { servidor } from '../../../../tests/servidor.js';
import { guardarArchivo } from '../../../utils/descarga.js';

vi.mock('../../../utils/descarga.js', () => ({ guardarArchivo: vi.fn() }));

const APROBADO = pago({
  estado: 'APROBADO',
  forma_en_linea: 'TARJETA_CREDITO',
  tarjeta_ultimos4: '3704',
  acreditado_en: '2026-11-16T15:05:00Z',
  numero_comprobante: 'PG-2026-000007',
});

async function completarTarjeta(user, numero) {
  await user.type(screen.getByLabelText(/Número de la tarjeta/), numero);
  await user.type(screen.getByLabelText(/Nombre del titular/), 'Sol Socia');
  await user.type(screen.getByLabelText(/Vencimiento/), '11/30');
  await user.type(screen.getByLabelText(/Código de seguridad/), '123');
}

describe('Pago de multas en línea (simulado)', () => {
  it('CA-DEV-22: el socio inicia el pago y va al checkout simulado', async () => {
    sesionDe(SOCIO);
    responder('get', '/multas', pagina([multa()]));
    const llamadas = registrar('post', '/multas/14/pagos', pago(), 201);
    responder('get', '/pagos/7', pago());
    const user = userEvent.setup();
    renderizarApp('/multas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Multas' });
    expect(within(tabla).getByText('Sin pagar')).toBeVisible();
    await user.click(within(tabla).getByRole('button', { name: /Pagar en línea/ }));

    expect(await screen.findByRole('group', { name: '¿Cómo querés pagar?' })).toBeVisible();
    expect(screen.getByText('$ 1.000,00')).toBeVisible();
    expect(llamadas).toHaveLength(1);
  });

  it('CA-DEV-22: con un pago en curso, el socio lo retoma', async () => {
    sesionDe(SOCIO);
    responder('get', '/multas', pagina([multa({ pago_en_curso: pago() })]));
    renderizarApp('/multas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Multas' });
    expect(within(tabla).getByText('Pago en línea en curso')).toBeVisible();
    expect(within(tabla).getByRole('button', { name: /Continuar el pago/ })).toBeVisible();
  });

  it('CA-DEV-23, CA-DEV-28: paga con tarjeta, solo envía los últimos 4 dígitos y descarga el comprobante', async () => {
    sesionDe(SOCIO);
    responder('get', '/pagos/7', pago());
    const llamadas = registrar('post', '/pagos/7/pagar', APROBADO);
    servidor.use(
      http.get('http://localhost/api/v1/pagos/7/comprobante', () =>
        HttpResponse.text('%PDF-1.4', {
          headers: {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'attachment; filename="comprobante-PG-2026-000007.pdf"',
          },
        }),
      ),
    );
    const user = userEvent.setup();
    const { container } = renderizarApp('/pagos/simulado?pago=7', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Continuar' }));
    // Con datos inválidos no envía nada.
    await user.click(screen.getByRole('button', { name: /Pagar \$/ }));
    expect(screen.getByText('Revisá el número de la tarjeta.')).toBeVisible();
    expect(llamadas).toHaveLength(0);
    await completarTarjeta(user, '4509953566233704');
    expect(screen.getByLabelText(/Número de la tarjeta \(Visa\)/)).toHaveValue(
      '4509 9535 6623 3704',
    );
    await user.click(screen.getByRole('button', { name: /Pagar \$/ }));

    expect(await screen.findByText(/la multa quedó saldada/)).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ forma: 'TARJETA_CREDITO', tarjeta_ultimos4: '3704' });
    expect(await axe(container)).toHaveNoViolations();

    await user.click(
      screen.getByRole('button', { name: /Descargar el comprobante PG-2026-000007/ }),
    );
    await vi.waitFor(() =>
      // El Blob de la respuesta es el de Node, no el de jsdom: alcanza con que llegue.
      expect(guardarArchivo).toHaveBeenCalledWith(
        expect.anything(),
        'comprobante-PG-2026-000007.pdf',
      ),
    );
  });

  it('CA-DEV-24: la tarjeta de prueba rechazada deja la multa pendiente y permite reintentar', async () => {
    sesionDe(SOCIO);
    responder('get', '/pagos/7', pago());
    responder(
      'post',
      '/pagos/7/pagar',
      pago({
        estado: 'RECHAZADO',
        forma_en_linea: 'TARJETA_DEBITO',
        tarjeta_ultimos4: '0002',
        motivo: 'Tarjeta rechazada por el emisor (tarjeta de prueba)',
      }),
    );
    const reintento = registrar('post', '/multas/14/pagos', pago({ id: 8 }), 201);
    responder('get', '/pagos/8', pago({ id: 8 }));
    const user = userEvent.setup();
    renderizarApp('/pagos/simulado?pago=7', { conSesion: true });

    await user.click(await screen.findByLabelText('Tarjeta de débito'));
    await user.click(screen.getByRole('button', { name: 'Continuar' }));
    await completarTarjeta(user, '4000000000000002');
    await user.click(screen.getByRole('button', { name: /Pagar \$/ }));

    expect(await screen.findByText(/Pago rechazado: Tarjeta rechazada/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Intentar de nuevo' }));
    expect(await screen.findByRole('group', { name: '¿Cómo querés pagar?' })).toBeVisible();
    expect(reintento).toHaveLength(1);
  });

  it('CA-DEV-28: con dinero en cuenta no pide tarjeta', async () => {
    sesionDe(SOCIO);
    responder('get', '/pagos/7', pago());
    const llamadas = registrar(
      'post',
      '/pagos/7/pagar',
      pago({ ...APROBADO, forma_en_linea: 'DINERO_EN_CUENTA', tarjeta_ultimos4: null }),
    );
    const user = userEvent.setup();
    renderizarApp('/pagos/simulado?pago=7', { conSesion: true });

    await user.click(await screen.findByLabelText('Dinero en cuenta'));
    await user.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(screen.queryByLabelText(/Número de la tarjeta/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Pagar \$/ }));

    expect(await screen.findByText(/la multa quedó saldada/)).toBeVisible();
    expect(llamadas[0].cuerpo).toEqual({ forma: 'DINERO_EN_CUENTA', tarjeta_ultimos4: null });
  });

  it('CA-DEV-27: una multa saldada ofrece su comprobante en la lista', async () => {
    sesionDe(SOCIO);
    responder(
      'get',
      '/multas',
      pagina([multa({ estado: 'SALDADA', fecha_saldada: '2026-11-16T15:05:00Z', pago: APROBADO })]),
    );
    renderizarApp('/multas', { conSesion: true });

    const tabla = await screen.findByRole('table', { name: 'Multas' });
    expect(
      within(tabla).getByRole('button', { name: 'Descargar el comprobante PG-2026-000007' }),
    ).toBeVisible();
  });
});
