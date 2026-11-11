import { DIAS } from '../../utils/formato.js';

export const MAX_FRANJAS_POR_DIA = 4;

/** `{1: [{apertura, cierre}], ...}` → lista plana con `dia_semana` (lo que espera la API). */
export function aplanarHorarios(porDia) {
  return DIAS.flatMap(({ numero }) =>
    (porDia[numero] ?? []).map((f) => ({
      dia_semana: numero,
      apertura: f.apertura,
      cierre: f.cierre,
    })),
  );
}

/** Lista plana de la API → `{1: [...], ..., 7: [...]}` con los siete días presentes. */
export function agruparHorarios(horarios = []) {
  const porDia = Object.fromEntries(DIAS.map(({ numero }) => [numero, []]));
  for (const franja of horarios) {
    porDia[franja.dia_semana].push({ apertura: franja.apertura, cierre: franja.cierre });
  }
  for (const franjas of Object.values(porDia))
    franjas.sort((a, b) => a.apertura.localeCompare(b.apertura));
  return porDia;
}

/**
 * Valida el horario mientras se escribe: cierre posterior a la apertura, hasta 4 franjas por día y
 * sin solapamientos (dos franjas contiguas, que cierran y abren a la misma hora, son válidas).
 *
 * @returns {Record<number, string[]>} problemas por día (solo los días con problemas)
 */
export function validarHorarios(porDia) {
  const problemas = {};
  const agregar = (dia, texto) => (problemas[dia] ??= []).push(texto);
  let hayFranjas = false;
  for (const { numero } of DIAS) {
    const franjas = porDia[numero] ?? [];
    hayFranjas ||= franjas.length > 0;
    if (franjas.length > MAX_FRANJAS_POR_DIA) agregar(numero, 'Un día admite hasta 4 franjas.');
    franjas.forEach((f, i) => {
      if (!f.apertura || !f.cierre) agregar(numero, `Complete la franja ${i + 1}.`);
      else if (f.cierre <= f.apertura)
        agregar(numero, `En la franja ${i + 1}, el cierre debe ser posterior a la apertura.`);
    });
    const completas = franjas
      .map((f, i) => ({ ...f, i }))
      .filter((f) => f.apertura && f.cierre && f.cierre > f.apertura)
      .sort((a, b) => a.apertura.localeCompare(b.apertura));
    for (let k = 1; k < completas.length; k += 1) {
      if (completas[k].apertura < completas[k - 1].cierre)
        agregar(
          numero,
          `Las franjas ${completas[k - 1].i + 1} y ${completas[k].i + 1} se solapan.`,
        );
    }
  }
  if (!hayFranjas) problemas.general = ['Cargue al menos una franja horaria.'];
  return problemas;
}
