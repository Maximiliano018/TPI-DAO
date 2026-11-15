import { describe, expect, it } from 'vitest';
import { formatearNumero, luhnValido, marca, vencimientoValido } from './tarjeta.js';

describe('Datos de tarjeta del checkout simulado', () => {
  it('valida el número con Luhn y lo agrupa de a cuatro', () => {
    expect(luhnValido('4509 9535 6623 3704')).toBe(true);
    expect(luhnValido('4000000000000002')).toBe(true);
    expect(luhnValido('4509 9535 6623 3705')).toBe(false);
    expect(luhnValido('1234')).toBe(false);
    expect(formatearNumero('4509953566233704999')).toBe('4509 9535 6623 3704');
    expect(marca('4509')).toBe('Visa');
    expect(marca('5031')).toBe('Mastercard');
  });

  it('acepta un vencimiento MM/AA hasta el último día del mes', () => {
    const hoy = new Date(2026, 10, 30);
    expect(vencimientoValido('11/26', hoy)).toBe(true);
    expect(vencimientoValido('10/26', hoy)).toBe(false);
    expect(vencimientoValido('13/30', hoy)).toBe(false);
    expect(vencimientoValido('1130', hoy)).toBe(false);
  });
});
