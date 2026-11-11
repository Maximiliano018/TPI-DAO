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

/** Respuesta de error con el formato de la API. */
export function error(estado, codigo, mensaje, detalles = []) {
  return HttpResponse.json({ error: { codigo, mensaje, detalles } }, { status: estado });
}

/** `/auth/me` devuelve esta persona (restaura la sesión guardada). */
export function sesionDe(usuario) {
  responder('get', '/auth/me', usuario);
}

export { HttpResponse, http };
