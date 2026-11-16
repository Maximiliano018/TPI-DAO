import { useState } from 'react';
import estilos from './Portada.module.css';

const LOMOS = [
  'rojo',
  'naranja',
  'amarillo',
  'verde',
  'turquesa',
  'azul',
  'indigo',
  'violeta',
  'rosa',
];
// Tapas claras: el texto va en tinta para que se lea.
const CLARAS = new Set(['naranja', 'amarillo', 'verde', 'rosa']);

/** Color de tapa estable para cada título (el mismo libro siempre del mismo color). */
function colorDe(titulo) {
  let suma = 0;
  for (const letra of titulo) suma = (suma * 31 + letra.charCodeAt(0)) % 997;
  return LOMOS[suma % LOMOS.length];
}

/**
 * Tapa de un libro: la imagen si la hay; si no (o si no carga), una tapa de tela con el título y
 * el autor, del mismo color que los lomos del menú.
 *
 * @param {{titulo: string, autores?: string[], portadaUrl?: string|null, tamano?: 'chica'|'mediana'|'grande', decorativa?: boolean}} props
 */
export default function Portada({
  titulo,
  autores = [],
  portadaUrl,
  tamano = 'mediana',
  decorativa = false,
}) {
  const [fallo, setFallo] = useState(false);
  const clase = `${estilos.portada} ${estilos[tamano]}`;
  if (portadaUrl && !fallo) {
    return (
      <img
        className={clase}
        src={portadaUrl}
        alt={decorativa ? '' : `Portada de ${titulo}`}
        loading="lazy"
        onError={() => setFallo(true)}
      />
    );
  }
  // Un autor, con nombre completo; varios, solo los apellidos («HUNT · THOMAS»).
  const autor =
    autores.length > 1 ? autores.map((a) => a.split(' ').at(-1)).join(' · ') : (autores[0] ?? '');
  const color = colorDe(titulo);
  return (
    <div
      className={`${clase} ${estilos.tela}`}
      style={{
        '--tapa': `var(--lomo-${color})`,
        '--tinta': CLARAS.has(color) ? 'var(--color-ink)' : '#fff',
      }}
      role={decorativa ? undefined : 'img'}
      aria-label={decorativa ? undefined : `Portada de ${titulo}`}
      aria-hidden={decorativa || undefined}
    >
      <span className={estilos.titulo}>{titulo}</span>
      {autor && <span className={estilos.autor}>{autor}</span>}
    </div>
  );
}
