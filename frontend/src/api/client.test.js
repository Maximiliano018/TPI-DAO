import { describe, expect, it, vi } from 'vitest';
import { error, responder } from '../../tests/handlers.js';
import { ApiError, alVencerLaSesion, api, guardarToken, leerToken } from './client.js';

describe('cliente de la API', () => {
  it('agrega el token y envía el cuerpo como JSON', async () => {
    guardarToken('abc');
    let visto;
    responder('post', '/sedes', async ({ request }) => {
      visto = { auth: request.headers.get('authorization'), cuerpo: await request.json() };
      return { id: 1 };
    });

    await api.post('/sedes', { nombre: 'X' });

    expect(visto).toEqual({ auth: 'Bearer abc', cuerpo: { nombre: 'X' } });
  });

  it('convierte el formato de error en un ApiError', async () => {
    responder('get', '/sedes/9', () =>
      error(404, 'SEDE_NO_ENCONTRADA', 'No existe', [{ campo: 'id' }]),
    );

    const fallo = await api.get('/sedes/9').catch((e) => e);

    expect(fallo).toBeInstanceOf(ApiError);
    expect(fallo).toMatchObject({
      estado: 404,
      codigo: 'SEDE_NO_ENCONTRADA',
      mensaje: 'No existe',
    });
    expect(fallo.detalles).toEqual([{ campo: 'id' }]);
  });

  it('arma la consulta ignorando valores vacíos', async () => {
    let url;
    responder('get', '/sedes', ({ request }) => {
      url = new URL(request.url);
      return { items: [] };
    });

    await api.get('/sedes', { q: 'cen', estado: '', page: 2, localidad_id: undefined });

    expect(url.search).toBe('?q=cen&page=2');
  });

  it('un 204 devuelve null', async () => {
    responder('delete', '/sedes/1/excepciones-horario/2', null, 204);

    expect(await api.delete('/sedes/1/excepciones-horario/2')).toBeNull();
  });

  it('ante un 401 de una solicitud autenticada avisa que la sesión venció', async () => {
    const aviso = vi.fn();
    alVencerLaSesion(aviso);
    guardarToken('vencido');
    responder('get', '/sedes', () => error(401, 'TOKEN_INVALIDO', 'Vencido'));

    await expect(api.get('/sedes')).rejects.toMatchObject({ estado: 401 });

    expect(aviso).toHaveBeenCalledOnce();
    alVencerLaSesion(() => {});
  });

  it('un error de red se informa como SIN_CONEXION', async () => {
    const { servidor } = await import('../../tests/servidor.js');
    const { http, HttpResponse } = await import('msw');
    servidor.use(http.get('http://localhost/api/v1/sedes', () => HttpResponse.error()));

    await expect(api.get('/sedes')).rejects.toMatchObject({ estado: 0, codigo: 'SIN_CONEXION' });
  });

  it('el token se guarda en sessionStorage y se descarta al limpiar', () => {
    guardarToken('t1');
    expect(sessionStorage.getItem('tpi.token')).toBe('t1');
    guardarToken(null);
    expect(leerToken()).toBeNull();
    expect(sessionStorage.getItem('tpi.token')).toBeNull();
  });
});
