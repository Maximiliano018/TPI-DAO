import { describe, expect, it } from 'vitest';
import { aCsv } from './csv.js';

describe('aCsv', () => {
  it('separa con punto y coma y escapa comillas, separadores y saltos de línea', () => {
    const columnas = [
      { titulo: 'Libro', valor: (f) => f.titulo },
      { titulo: 'Préstamos', valor: (f) => f.n },
    ];
    const texto = aCsv(columnas, [
      { titulo: 'Rayuela', n: 4 },
      { titulo: 'El "Aleph"; cuentos', n: null },
    ]);

    expect(texto.split('\r\n')).toEqual([
      'Libro;Préstamos',
      'Rayuela;4',
      '"El ""Aleph""; cuentos";',
    ]);
  });
});
