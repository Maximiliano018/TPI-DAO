/** Estantería vacía con un libro caído: para los estados «sin resultados». Decorativa. */
export function EstanteriaVacia({ ancho = 160 }) {
  return (
    <svg
      width={ancho}
      viewBox="0 0 160 96"
      aria-hidden="true"
      focusable="false"
      style={{ display: 'block' }}
    >
      <rect x="6" y="8" width="148" height="76" rx="3" style={{ fill: 'var(--color-wood-800)' }} />
      <rect x="12" y="14" width="136" height="64" style={{ fill: 'var(--color-wood-900)' }} />
      <rect x="2" y="78" width="156" height="12" rx="2" style={{ fill: 'var(--color-wood-400)' }} />
      <rect
        x="2"
        y="78"
        width="156"
        height="3"
        style={{ fill: 'var(--color-brass)', opacity: 0.6 }}
      />
      <g transform="rotate(-14 112 74)">
        <rect
          x="98"
          y="38"
          width="14"
          height="40"
          rx="1.5"
          style={{ fill: 'var(--lomo-burdeos)' }}
        />
        <rect x="98" y="46" width="14" height="2" style={{ fill: 'var(--color-brass)' }} />
        <rect x="98" y="66" width="14" height="2" style={{ fill: 'var(--color-brass)' }} />
      </g>
      <rect x="120" y="50" width="12" height="28" rx="1.5" style={{ fill: 'var(--lomo-marino)' }} />
      <rect x="120" y="56" width="12" height="2" style={{ fill: 'var(--color-brass)' }} />
      <rect x="22" y="64" width="46" height="14" rx="1.5" style={{ fill: 'var(--lomo-bosque)' }} />
      <rect x="64" y="64" width="4" height="14" style={{ fill: 'var(--color-cream)' }} />
      <rect x="26" y="68" width="2" height="6" style={{ fill: 'var(--color-brass)' }} />
    </svg>
  );
}
