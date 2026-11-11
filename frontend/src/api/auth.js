import { api, solicitar } from './client.js';

/** Inicia sesión; devuelve `{ access_token, usuario }`. */
export function iniciarSesion(username, password) {
  return solicitar('/auth/login', {
    method: 'POST',
    body: { username, password },
    autenticada: false,
  });
}

/** Usuario de la sesión con su sede y sus permisos. */
export function obtenerYo() {
  return api.get('/auth/me');
}
