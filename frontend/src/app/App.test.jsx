import { render, screen } from '@testing-library/react';
import App from './App.jsx';

describe('App', () => {
  it('muestra el título del sistema', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: /préstamos interbibliotecarios/i }),
    ).toBeInTheDocument();
  });
});
