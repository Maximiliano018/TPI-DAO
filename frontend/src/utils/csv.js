const NUMERO = /^-?\d+([.,]\d+)?$/;

/**
 * Una celda CSV: entre comillas si tiene separador, comillas o saltos de línea. Un texto que
 * empieza con `=`, `+`, `-`, `@`, tabulación o retorno lleva delante un apóstrofo, para que la
 * planilla no lo ejecute como fórmula (inyección de CSV); los números negativos quedan igual.
 */
function celda(valor) {
  let texto = valor === null || valor === undefined ? '' : String(valor);
  if (/^[=+\-@\t\r]/.test(texto) && !NUMERO.test(texto)) texto = `'${texto}`;
  return /[";\n\r]/.test(texto) ? `"${texto.replaceAll('"', '""')}"` : texto;
}

/**
 * Texto CSV con `;` como separador (lo abre bien una planilla en español).
 * `columnas` es `[{ titulo, valor: (fila) => ... }]`.
 */
export function aCsv(columnas, filas) {
  const lineas = [columnas.map((c) => celda(c.titulo)).join(';')];
  for (const fila of filas) lineas.push(columnas.map((c) => celda(c.valor(fila))).join(';'));
  return lineas.join('\r\n');
}

/** Descarga el CSV en el navegador (con BOM para que la planilla respete los acentos). */
export function descargarCsv(nombre, columnas, filas) {
  const blob = new Blob(['﻿', aCsv(columnas, filas)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = `${nombre}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
}
