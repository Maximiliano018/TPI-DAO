import { describe, expect, it } from 'vitest';
import { diaSemanaISO, formatearFecha, formatearFechaHora, textoHorarioDelDia } from './formato.js';

describe('formato', () => {
  it('fecha y fecha-hora en formato local', () => {
    expect(formatearFecha('2026-12-25')).toBe('25/12/2026');
    expect(formatearFechaHora('2026-12-25T10:30:00')).toBe('25/12/2026 10:30');
    expect(formatearFecha(null)).toBe('');
  });

  it('el día ISO va de lunes (1) a domingo (7)', () => {
    expect(diaSemanaISO(new Date(2026, 10, 9))).toBe(1); // lunes
    expect(diaSemanaISO(new Date(2026, 10, 15))).toBe(7); // domingo
  });

  it('el horario del día une las franjas ordenadas o dice Cerrado', () => {
    const horarios = [
      { dia_semana: 1, apertura: '15:00', cierre: '19:00' },
      { dia_semana: 1, apertura: '09:00', cierre: '13:00' },
    ];
    expect(textoHorarioDelDia(horarios, 1)).toBe('09:00–13:00 · 15:00–19:00');
    expect(textoHorarioDelDia(horarios, 2)).toBe('Cerrado');
  });
});
