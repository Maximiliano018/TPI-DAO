import { z } from 'zod';
import { fechaLocalISO } from '../../utils/formato.js';

// El frontend valida forma y obligatoriedad; las reglas (duplicados, sede activa) son del backend.
const texto = (campo, maximo = 100) =>
  z
    .string()
    .trim()
    .min(1, `El ${campo} es obligatorio`)
    .max(maximo, `El ${campo} no puede superar los ${maximo} caracteres`);

const opcional = (esquema) => z.union([z.literal(''), esquema]);

export const TIPOS_DE_DOCUMENTO = ['DNI', 'LE', 'LC', 'PASAPORTE'];

export const esquemaSocio = z
  .object({
    tipo_documento: z.enum(TIPOS_DE_DOCUMENTO, { error: 'Elija el tipo de documento' }),
    nro_documento: z.string().trim().min(1, 'El número de documento es obligatorio'),
    nombre: texto('nombre'),
    apellido: texto('apellido'),
    fecha_nacimiento: opcional(
      z.string().refine((v) => v <= fechaLocalISO(), 'La fecha de nacimiento no puede ser futura'),
    ),
    email: opcional(z.email('El correo electrónico no tiene un formato válido')),
    telefono: opcional(
      z
        .string()
        .trim()
        .regex(/^\+?[\d\s\-()]{8,20}$/, 'Use el formato internacional, por ejemplo +543515000000'),
    ),
    domicilio: z.string().trim().max(200, 'El domicilio no puede superar los 200 caracteres'),
    sede_alta_id: z.number().optional(),
  })
  .superRefine((datos, ctx) => {
    if (!datos.email && !datos.telefono) {
      ctx.addIssue({
        code: 'custom',
        path: ['email'],
        message: 'Indique al menos un correo o un teléfono de contacto',
      });
    }
  });

export const esquemaMotivo = z.object({
  motivo: z
    .string()
    .trim()
    .min(5, 'El motivo debe tener entre 5 y 300 caracteres')
    .max(300, 'El motivo debe tener entre 5 y 300 caracteres'),
});

export const esquemaCuenta = z
  .object({
    username: z
      .string()
      .trim()
      .regex(
        /^[A-Za-z0-9._-]{3,50}$/,
        'Use de 3 a 50 caracteres: letras, números, punto o guiones',
      ),
    password: z
      .string()
      .min(10, 'La contraseña debe tener entre 10 y 128 caracteres')
      .max(128, 'La contraseña debe tener entre 10 y 128 caracteres')
      .refine((v) => /[A-Za-z]/.test(v) && /\d/.test(v), {
        message: 'La contraseña debe incluir al menos una letra y un número',
      }),
    confirmacion: z.string(),
  })
  .refine((datos) => datos.confirmacion === datos.password, {
    path: ['confirmacion'],
    message: 'Las contraseñas no coinciden',
  });

/** Mensaje opcional de la solicitud de reactivación. */
export const esquemaSolicitud = z.object({
  mensaje: z.string().trim().max(300, 'El mensaje no puede superar los 300 caracteres'),
});
