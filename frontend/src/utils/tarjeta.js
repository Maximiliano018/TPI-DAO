// Validación de los datos de tarjeta del checkout simulado. Nada de esto se envía al servidor:
// solo viajan los últimos 4 dígitos.

/** Solo los dígitos del número. */
export const digitos = (numero) => numero.replace(/\D/g, '');

/** `4509953566233704` → `4509 9535 6623 3704` (hasta 16 dígitos). */
export const formatearNumero = (numero) =>
  digitos(numero)
    .slice(0, 16)
    .replace(/(\d{4})(?=\d)/g, '$1 ');

/** Algoritmo de Luhn: detecta errores de tipeo en el número. */
export function luhnValido(numero) {
  const d = digitos(numero);
  if (d.length < 15 || d.length > 16) return false;
  let suma = 0;
  for (let i = 0; i < d.length; i += 1) {
    let n = Number(d[d.length - 1 - i]);
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    suma += n;
  }
  return suma % 10 === 0;
}

/** `MM/AA` no vencido (vale hasta el último día del mes). */
export function vencimientoValido(texto, hoy = new Date()) {
  const partes = /^(\d{2})\/(\d{2})$/.exec(texto);
  if (!partes) return false;
  const mes = Number(partes[1]);
  const anio = 2000 + Number(partes[2]);
  if (mes < 1 || mes > 12) return false;
  return new Date(anio, mes, 0, 23, 59, 59) >= hoy;
}

/** Marca por el primer dígito (solo para mostrar). */
export function marca(numero) {
  const d = digitos(numero);
  if (d.startsWith('4')) return 'Visa';
  if (/^5[0-5]/.test(d)) return 'Mastercard';
  if (/^3[47]/.test(d)) return 'American Express';
  return null;
}
