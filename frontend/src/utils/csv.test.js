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

  it('antepone un apóstrofo a lo que una planilla ejecutaría como fórmula', () => {
    const columnas = [{ titulo: 'Valor', valor: (f) => f }];
    const texto = aCsv(columnas, ['=1+1', '+5 días', '-x', '@SUMA(A1)', '-3', '4,5', 'Rayuela']);

    expect(texto.split('\r\n').slice(1)).toEqual([
      "'=1+1",
      "'+5 días",
      "'-x",
      "'@SUMA(A1)",
      '-3',
      '4,5',
      'Rayuela',
    ]);
  });
});
