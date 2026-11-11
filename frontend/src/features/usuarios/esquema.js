import { z } from 'zod';

const nombre = z
  .string()
  .trim()
  .min(3, 'El nombre debe tener entre 3 y 100 caracteres')
  .max(100, 'El nombre debe tener entre 3 y 100 caracteres');

const sede = z.number({ error: 'Elija la sede del bibliotecario' }).optional();

// Un bibliotecario necesita sede; un administrador no la tiene (se ignora si quedó elegida).
function exigirSedeAlBibliotecario(datos, ctx) {
  if (datos.rol === 'BIBLIOTECARIO' && datos.sede_id === undefined) {
    ctx.addIssue({ code: 'custom', path: ['sede_id'], message: 'Elija la sede del bibliotecario' });
  }
}

export const esquemaCrearUsuario = z
  .object({
    username: z
      .string()
      .trim()
      .regex(
        /^[A-Za-z0-9._-]{3,50}$/,
        'Use de 3 a 50 caracteres: letras, números, punto o guiones',
      ),
    nombre,
    password: z
      .string()
      .min(10, 'La contraseña debe tener entre 10 y 128 caracteres')
      .max(128, 'La contraseña debe tener entre 10 y 128 caracteres')
      .refine((v) => /[A-Za-z]/.test(v) && /\d/.test(v), {
        message: 'La contraseña debe incluir al menos una letra y un número',
      }),
    confirmacion: z.string(),
    rol: z.enum(['ADMIN', 'BIBLIOTECARIO'], { error: 'Elija el rol' }),
    sede_id: sede,
  })
  .superRefine((datos, ctx) => {
    if (datos.confirmacion !== datos.password) {
      ctx.addIssue({
        code: 'custom',
        path: ['confirmacion'],
        message: 'Las contraseñas no coinciden',
      });
    }
    exigirSedeAlBibliotecario(datos, ctx);
  });

/** En la edición el rol no cambia: viaja en el formulario solo para validar la sede. */
export const esquemaEditarUsuario = z
  .object({ nombre, rol: z.enum(['ADMIN', 'BIBLIOTECARIO']), sede_id: sede })
  .superRefine(exigirSedeAlBibliotecario);
