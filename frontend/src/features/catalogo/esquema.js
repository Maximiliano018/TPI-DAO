import { z } from 'zod';

// El frontend valida forma y obligatoriedad; el ISBN y los duplicados los valida el backend.
export const esquemaLibro = z.object({
  isbn: z
    .string()
    .trim()
    .refine((v) => v === '' || /^[\dXx\s-]{10,17}$/.test(v), 'Revise el ISBN: 10 o 13 dígitos'),
  titulo: z
    .string()
    .trim()
    .min(1, 'El título es obligatorio')
    .max(200, 'El título admite hasta 200 caracteres'),
  autores: z
    .string()
    .refine((v) => v.split('\n').some((a) => a.trim()), 'Indique al menos un autor'),
  editorial: z.string().trim().max(100, 'La editorial admite hasta 100 caracteres'),
  anio_edicion: z.union([
    z.literal(''),
    z.coerce.number().int('Indique un año').min(1450, 'Año inválido').max(2100, 'Año inválido'),
  ]),
  categoria_id: z.number({ error: 'Elija una categoría' }),
  tipo_material: z.enum(['LIBRO', 'REVISTA', 'OBRA_DE_REFERENCIA', 'OTRO']),
});

export const esquemaEjemplar = z.object({
  libro_id: z.number({ error: 'Elija el libro' }),
  codigo_inventario: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9][A-Za-z0-9-]{2,29}$/, 'De 3 a 30 letras, números o guiones'),
  estado_fisico: z.enum(['NUEVO', 'BUENO', 'REGULAR', 'DANADO']),
  observaciones: z.string().trim().max(300, 'Hasta 300 caracteres'),
  sede_id: z.number().optional(),
});

export const esquemaEstadoFisico = z.object({
  estado_fisico: z.enum(['NUEVO', 'BUENO', 'REGULAR', 'DANADO']),
  observaciones: z.string().trim().max(300, 'Hasta 300 caracteres'),
});
