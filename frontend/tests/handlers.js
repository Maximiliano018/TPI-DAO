import { http, HttpResponse } from 'msw';
import { servidor } from './servidor.js';

const BASE = 'http://localhost/api/v1';

/** Agrega handlers de MSW para la prueba en curso. */
export function responder(metodo, ruta, respuesta, estado = 200) {
  servidor.use(
    http[metodo](`${BASE}${ruta}`, (info) => {
      const cuerpo = typeof respuesta === 'function' ? respuesta(info) : respuesta;
      if (cuerpo instanceof Response) return cuerpo;
      return estado === 204
        ? new HttpResponse(null, { status: 204 })
        : HttpResponse.json(cuerpo, { status: estado });
    }),
  );
}

/**
 * Como `responder`, pero registra cada llamada (`{url, cuerpo}`) y devuelve la lista. Con una
 * función, recibe la llamada y puede responder distinto según cuántas hubo (`llamadas.length`).
 */
export function registrar(metodo, ruta, respuesta, estado = 200) {
  const llamadas = [];
  servidor.use(
    http[metodo](`${BASE}${ruta}`, async ({ request }) => {
      const texto = await request.text();
      llamadas.push({ url: new URL(request.url), cuerpo: texto ? JSON.parse(texto) : null });
      const cuerpo =
        typeof respuesta === 'function' ? respuesta(llamadas.at(-1), llamadas) : respuesta;
      if (cuerpo instanceof Response) return cuerpo;
      return estado === 204
        ? new HttpResponse(null, { status: 204 })
        : HttpResponse.json(cuerpo, { status: estado });
    }),
  );
  return llamadas;
}

/** Respuesta de error con el formato de la API. */
export function error(estado, codigo, mensaje, detalles = []) {
  return HttpResponse.json({ error: { codigo, mensaje, detalles } }, { status: estado });
}

/** `/auth/me` devuelve esta persona (restaura la sesión guardada). */
export function sesionDe(usuario) {
  responder('get', '/auth/me', usuario);
}

export { HttpResponse, http };
