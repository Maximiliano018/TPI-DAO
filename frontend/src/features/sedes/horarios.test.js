import { describe, expect, it } from 'vitest';
import { agruparHorarios, aplanarHorarios, validarHorarios } from './horarios.js';

const vacio = () => agruparHorarios([]);

describe('horarios', () => {
  it('agrupa por día con los siete días presentes y ordena las franjas', () => {
    const porDia = agruparHorarios([
      { dia_semana: 1, apertura: '15:00', cierre: '19:00' },
      { dia_semana: 1, apertura: '09:00', cierre: '13:00' },
    ]);
    expect(Object.keys(porDia)).toHaveLength(7);
    expect(porDia[1].map((f) => f.apertura)).toEqual(['09:00', '15:00']);
    expect(porDia[2]).toEqual([]);
  });

  it('aplana al formato de la API', () => {
    const porDia = vacio();
    porDia[3] = [{ apertura: '09:00', cierre: '13:00' }];
    expect(aplanarHorarios(porDia)).toEqual([
      { dia_semana: 3, apertura: '09:00', cierre: '13:00' },
    ]);
  });

  it('exige al menos una franja', () => {
    expect(validarHorarios(vacio()).general).toBeDefined();
  });

  it('marca cierre anterior a la apertura y franjas incompletas', () => {
    const porDia = vacio();
    porDia[1] = [{ apertura: '13:00', cierre: '09:00' }];
    porDia[2] = [{ apertura: '09:00', cierre: '' }];
    const problemas = validarHorarios(porDia);
    expect(problemas[1][0]).toMatch(/cierre debe ser posterior/);
    expect(problemas[2][0]).toMatch(/Complete la franja 1/);
  });

  it('marca solapamientos pero acepta franjas contiguas', () => {
    const porDia = vacio();
    porDia[1] = [
      { apertura: '09:00', cierre: '13:00' },
      { apertura: '12:00', cierre: '15:00' },
    ];
    porDia[2] = [
      { apertura: '09:00', cierre: '13:00' },
      { apertura: '13:00', cierre: '15:00' },
    ];
    const problemas = validarHorarios(porDia);
    expect(problemas[1][0]).toMatch(/se solapan/);
    expect(problemas[2]).toBeUndefined();
  });

  it('admite hasta 4 franjas por día', () => {
    const porDia = vacio();
    porDia[1] = ['08:00', '10:00', '12:00', '14:00', '16:00'].map((a, i) => ({
      apertura: a,
      cierre: `${String(9 + i * 2).padStart(2, '0')}:30`,
    }));
    expect(validarHorarios(porDia)[1]).toContain('Un día admite hasta 4 franjas.');
  });
});
