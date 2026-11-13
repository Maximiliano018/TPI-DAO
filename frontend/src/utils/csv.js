/** Una celda CSV: entre comillas si tiene separador, comillas o saltos de línea. */
function celda(valor) {
  const texto = valor === null || valor === undefined ? '' : String(valor);
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
