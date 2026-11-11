import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../src/app/App.jsx';
import Providers, { crearQueryClient } from '../src/app/Providers.jsx';
import { guardarToken } from '../src/api/client.js';

/**
 * Renderiza la aplicación completa en una ruta. Con `usuario`, deja una sesión guardada: el
 * proveedor la restaura con `GET /auth/me` (el handler lo agrega el llamador).
 */
export function renderizarApp(ruta = '/', { conSesion = false } = {}) {
  guardarToken(conSesion ? 'token-de-prueba' : null);
  const queryClient = crearQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Providers queryClient={queryClient}>
        <App />
      </Providers>
    </MemoryRouter>,
  );
}

/** Renderiza un componente suelto con router, caché y sesión vacíos. */
export function renderizarConProveedores(ui, { ruta = '/' } = {}) {
  const queryClient = crearQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Providers queryClient={queryClient}>{ui}</Providers>
    </MemoryRouter>,
  );
}
