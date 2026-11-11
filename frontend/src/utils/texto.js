/** Minúsculas y sin tildes, para buscar sin distinguir mayúsculas ni acentos. */
export function normalizar(texto) {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}
