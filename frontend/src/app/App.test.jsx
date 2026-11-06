import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';

function renderizar(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('muestra el título del sistema en el inicio', () => {
    renderizar('/');
    expect(
      screen.getByRole('heading', { name: /préstamos interbibliotecarios/i }),
    ).toBeInTheDocument();
  });

  it('en /version muestra el backend en línea con su versión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ servicio: 'backend', estado: 'ok', version: '9.9.9' }),
      }),
    );
    renderizar('/version');

    expect(await screen.findByText('9.9.9')).toBeInTheDocument();
    expect(screen.getAllByText('En línea')).toHaveLength(2);
  });

  it('en /version informa si el backend no responde', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('fallo de red')));
    renderizar('/version');

    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
  });
});
