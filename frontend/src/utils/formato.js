import { format, parseISO } from 'date-fns';

/** Fecha `dd/mm/aaaa` a partir de `aaaa-mm-dd` o de un instante ISO. */
export function formatearFecha(valor) {
  if (!valor) return '';
  return format(parseISO(valor), 'dd/MM/yyyy');
}

/** Fecha y hora `dd/mm/aaaa HH:mm` en la zona del navegador. */
export function formatearFechaHora(valor) {
  if (!valor) return '';
  return format(parseISO(valor), 'dd/MM/yyyy HH:mm');
}

/** Fecha local `aaaa-mm-dd` (para inputs y comparaciones). */
export function fechaLocalISO(fecha = new Date()) {
  return format(fecha, 'yyyy-MM-dd');
}

const PESOS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });

/** Monto en pesos (`$ 1.000,00`) a partir del decimal en texto de la API. */
export function formatearMonto(valor) {
  if (valor === null || valor === undefined || valor === '') return '';
  return PESOS.format(Number(valor));
}

export const DIAS = [
  { numero: 1, nombre: 'Lunes' },
  { numero: 2, nombre: 'Martes' },
  { numero: 3, nombre: 'Miércoles' },
  { numero: 4, nombre: 'Jueves' },
  { numero: 5, nombre: 'Viernes' },
  { numero: 6, nombre: 'Sábado' },
  { numero: 7, nombre: 'Domingo' },
];

/** Día de la semana ISO (1 = lunes ... 7 = domingo) de una fecha. */
export function diaSemanaISO(fecha = new Date()) {
  const dia = fecha.getDay();
  return dia === 0 ? 7 : dia;
}

/** Franjas de un día, ordenadas por apertura. */
export function franjasDelDia(horarios, dia) {
  return horarios
    .filter((franja) => franja.dia_semana === dia)
    .sort((a, b) => a.apertura.localeCompare(b.apertura));
}

/** Texto del horario de un día: `09:00–13:00 · 15:00–19:00` o `Cerrado`. */
export function textoHorarioDelDia(horarios, dia) {
  const franjas = franjasDelDia(horarios, dia);
  if (franjas.length === 0) return 'Cerrado';
  return franjas.map((f) => `${f.apertura}–${f.cierre}`).join(' · ');
}
