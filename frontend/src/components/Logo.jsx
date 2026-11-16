/** Tres lomos de colores, de alturas distintas: logotipo del sistema. Decorativo (el nombre va en el texto). */
export default function Logo({ tamano = 32, className = '' }) {
  return (
    <svg
      className={className}
      width={tamano}
      height={tamano}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="3" y="9" width="7" height="21" rx="1" style={{ fill: 'var(--lomo-burdeos)' }} />
      <rect x="12.5" y="3" width="7" height="27" rx="1" style={{ fill: 'var(--lomo-marino)' }} />
      <rect x="22" y="7" width="7" height="23" rx="1" style={{ fill: 'var(--lomo-ocre)' }} />
    </svg>
  );
}
