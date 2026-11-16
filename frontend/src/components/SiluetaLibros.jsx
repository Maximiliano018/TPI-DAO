import estilos from './SiluetaLibros.module.css';

/**
 * Silueta de libros sobre el pie, como el horizonte de una ciudad: dos capas de lomos de alturas
 * distintas (alguno apoyado y alguna pila acostada) que pasan del gris claro al turquesa oscuro.
 */
export default function SiluetaLibros() {
  const ANCHO = 1440;
  const BASE = 150;
  const capas = [
    { color: 'rgba(42, 112, 117, 0.35)', semilla: 3, alto: 1 },
    { color: 'var(--color-marino)', semilla: 11, alto: 0.72 },
  ];
  return (
    <svg
      className={estilos.silueta}
      viewBox={`0 0 ${ANCHO} ${BASE}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      {capas.map((capa, c) => {
        const piezas = [];
        let x = c === 0 ? 6 : 0;
        for (let k = 0; x < ANCHO; k += 1) {
          if ((k + c) % 11 === 7) {
            [0, 1, 2].forEach((n) => {
              const largo = 70 - n * 8 + ((k + n) % 3) * 4;
              piezas.push(
                <rect
                  key={`${k}-${n}`}
                  x={x + n * 4}
                  y={BASE - (n + 1) * 13}
                  width={largo}
                  height={12}
                  rx="2"
                />,
              );
            });
            x += 80;
            continue;
          }
          const w = 22 + ((k * 37 + capa.semilla * 3) % 44);
          const h = (44 + ((k * 53 + capa.semilla * 7) % 86)) * capa.alto;
          const apoyado = (k + c) % 9 === 4;
          piezas.push(
            <rect
              key={k}
              x={x}
              y={BASE - h}
              width={w}
              height={h}
              rx="2"
              transform={apoyado ? `rotate(-8 ${x + w} ${BASE})` : undefined}
            />,
          );
          x += w + 3 + ((k * 11) % 5) + (apoyado ? 12 : 0);
        }
        return (
          <g key={c} fill={capa.color}>
            {piezas}
          </g>
        );
      })}
      <rect x="0" y={BASE - 6} width={ANCHO} height="6" fill="var(--color-marino)" />
    </svg>
  );
}
