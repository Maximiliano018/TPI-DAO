/** Libro abierto con marcador: logotipo del sistema. Decorativo (el nombre va en el texto). */
export default function Logo({ tamano = 32, className = '' }) {
  const hoja = { fill: 'var(--color-cream)', stroke: 'var(--color-brass)', strokeWidth: 1.2 };
  return (
    <svg
      className={className}
      width={tamano}
      height={tamano}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M16 9C13 6.8 9 6 4 6.6v18.6c5-.6 9 .2 12 2.4z" style={hoja} strokeLinejoin="round" />
      <path
        d="M16 9c3-2.2 7-3 12-2.4v18.6c-5-.6-9 .2-12 2.4z"
        style={hoja}
        strokeLinejoin="round"
      />
      <path
        d="M7 10.5c2.2-.2 4.4.2 6.5 1.2M7 14c2.2-.2 4.4.2 6.5 1.2M7 17.5c2.2-.2 4.4.2 6.5 1.2"
        style={{ stroke: 'var(--color-border-strong)', strokeWidth: 1, fill: 'none' }}
        strokeLinecap="round"
      />
      <path
        d="M19 9.2c1.8-.8 3.8-1.1 6-1v5l-3-1.6-3 1.6z"
        style={{ fill: 'var(--color-marcador)' }}
      />
    </svg>
  );
}
