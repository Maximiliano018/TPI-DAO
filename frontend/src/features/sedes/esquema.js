import { z } from 'zod';

const requerido = (mensaje) => z.string().trim().min(1, mensaje);

/** Validación del formulario de sede (los horarios se validan con `validarHorarios`). */
export const esquemaSede = z.object({
  codigo: z
    .string()
    .trim()
    .regex(
      /^[A-Za-z0-9_]{3,15}$/,
      'El código debe tener de 3 a 15 caracteres: letras, números o guion bajo',
    ),
  nombre: z
    .string()
    .trim()
    .min(3, 'El nombre debe tener entre 3 y 100 caracteres')
    .max(100, 'El nombre debe tener entre 3 y 100 caracteres'),
  calle: z
    .string()
    .trim()
    .min(2, 'La calle debe tener entre 2 y 100 caracteres')
    .max(100, 'La calle debe tener entre 2 y 100 caracteres'),
  numero: z
    .string()
    .trim()
    .regex(/^(\d{1,6}[A-Za-z]?|[Ss]\/[Nn])$/, 'Use el número de puerta (1250, 1250B) o S/N'),
  localidad_id: z.number({ error: 'Elija una localidad de la lista' }),
  telefono: z
    .string()
    .trim()
    .refine((v) => /^\+[1-9][0-9]{7,14}$/.test(v.replace(/[\s\-().]/g, '')), {
      message: 'Use el formato internacional, por ejemplo +54 351 422 1234',
    }),
  email: z.string().trim().email('El correo electrónico no tiene un formato válido'),
  responsable: z
    .string()
    .trim()
    .min(3, 'El responsable debe tener entre 3 y 100 caracteres')
    .max(100, 'El responsable debe tener entre 3 y 100 caracteres'),
});

/** Cierre por fecha o rango (modal del detalle). */
export const esquemaExcepcion = z
  .object({
    fecha_desde: requerido('Ingrese la fecha'),
    fecha_hasta: z.string(),
    tipo: z.enum(['CIERRE_TOTAL', 'CIERRE_PARCIAL']),
    hora_desde: z.string(),
    hora_hasta: z.string(),
    motivo: z.string().max(1000, 'El motivo admite hasta 1000 caracteres'),
  })
  .superRefine((d, ctx) => {
    const problema = (path, message) => ctx.addIssue({ code: 'custom', path: [path], message });
    if (d.fecha_hasta && d.fecha_desde) {
      const dias = (Date.parse(d.fecha_hasta) - Date.parse(d.fecha_desde)) / 86_400_000;
      if (dias < 0) problema('fecha_hasta', 'La fecha final no puede ser anterior a la inicial');
      else if (dias + 1 > 31) problema('fecha_hasta', 'El rango admite hasta 31 días');
    }
    if (d.tipo === 'CIERRE_PARCIAL') {
      if (!d.hora_desde) problema('hora_desde', 'Ingrese la hora de inicio');
      if (!d.hora_hasta) problema('hora_hasta', 'Ingrese la hora de fin');
      if (d.hora_desde && d.hora_hasta && d.hora_hasta <= d.hora_desde)
        problema('hora_hasta', 'La hora de fin debe ser posterior a la de inicio');
    }
  });
