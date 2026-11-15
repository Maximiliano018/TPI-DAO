import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

/**
 * Servidor MSW compartido: cada prueba agrega sus handlers con `servidor.use(...)`. Las cifras del
 * inicio público (que también muestra el login) responden siempre, salvo que la prueba las cambie.
 */
export const servidor = setupServer(
  http.get('http://localhost/api/v1/publico/inicio', () =>
    HttpResponse.json({ sedes_activas: 0, libros: 0, ejemplares: 0, destacados: [] }),
  ),
);
