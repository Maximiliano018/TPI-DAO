import { describe, expect, it } from 'vitest';
import { erroresPorCampo, mensajeDeError } from './errores.js';

describe('errores', () => {
  it('usa el mensaje amigable de un código conocido', () => {
    expect(mensajeDeError({ codigo: 'SEDE_CODIGO_DUPLICADO', mensaje: 'x' })).toBe(
      'Ya existe una sede con ese código',
    );
  });

  it('si el código no está, muestra el mensaje del backend', () => {
    expect(mensajeDeError({ codigo: 'RARO', mensaje: 'Algo raro pasó' })).toBe('Algo raro pasó');
  });

  it('agrupa los problemas por campo y conserva el primero', () => {
    const error = {
      detalles: [
        { campo: 'telefono', problema: 'Formato inválido' },
        { campo: 'telefono', problema: 'Otro' },
        { campo: 'email', problema: 'Inválido' },
        { sede: 1 },
      ],
    };
    expect(erroresPorCampo(error)).toEqual({ telefono: 'Formato inválido', email: 'Inválido' });
  });
});
