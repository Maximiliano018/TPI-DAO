import estilos from './Biblioteca.module.css';

// Paleta armónica con el turquesa: coral, arena, mostaza, salvia, petróleo, rosa viejo, crema…
const COLORES = [
  '#e76f51',
  '#f4a261',
  '#e9c46a',
  '#8ab17d',
  '#264653',
  '#e5989b',
  '#5c7d9b',
  '#f6efe2',
  '#b5838d',
  '#2f4858',
];
const MADERA = { marco: '#f0cfa0', sombra: '#d9a96f', fondo: '#fbf2e4', tabla: '#e6bd88' };

// Mueble: interior de x 166 a 464; cuatro estantes de 63 de alto.
const IZQ = 166;
const DER = 464;
const ALTO = 63;
const ESTANTES = [112, 185, 258, 331];

/** Números pseudoaleatorios con semilla: la biblioteca se dibuja siempre igual. */
function aleatorio(semilla) {
  let s = semilla;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

/** Lomos de un tramo del estante, sin dos colores iguales seguidos. */
function lomos(azar, desde, hasta, piso, previo = { color: '' }) {
  const piezas = [];
  let x = desde;
  while (x < hasta) {
    const w = 10 + Math.floor(azar() * 11);
    if (x + w > hasta) break;
    let color = COLORES[Math.floor(azar() * COLORES.length)];
    if (color === previo.color) color = COLORES[(COLORES.indexOf(color) + 3) % COLORES.length];
    previo.color = color;
    const h = Math.round(ALTO * (0.68 + azar() * 0.27));
    piezas.push({
      x,
      y: piso - h,
      w,
      h,
      color,
      banda: azar() < 0.45,
      etiqueta: w >= 15 && azar() < 0.4,
    });
    x += w + 1.5;
  }
  return piezas;
}

const azar = aleatorio(11);
const piso = (k) => ESTANTES[k] + ALTO;
const TRAMOS = [
  lomos(azar, IZQ + 4, 418, piso(0)),
  [...lomos(azar, IZQ + 4, 322, piso(1)), ...lomos(azar, 392, DER - 2, piso(1))],
  lomos(azar, 230, DER - 4, piso(2)),
  lomos(azar, IZQ + 4, DER - 4, piso(3)),
];

/** Lomo de pie con una banda clara y, a veces, una etiqueta. */
function Lomo({ p }) {
  const claro = p.color === '#f6efe2' || p.color === '#e9c46a';
  const detalle = claro ? 'rgba(38,70,83,0.35)' : 'rgba(255,255,255,0.55)';
  return (
    <g>
      <rect x={p.x} y={p.y} width={p.w} height={p.h} rx="2" fill={p.color} />
      <rect x={p.x + p.w - 2.5} y={p.y} width="2.5" height={p.h} fill="rgba(0,0,0,0.1)" />
      {p.banda && (
        <>
          <rect x={p.x} y={p.y + 6} width={p.w} height="2.5" fill={detalle} />
          <rect x={p.x} y={p.y + p.h - 9} width={p.w} height="2.5" fill={detalle} />
        </>
      )}
      {p.etiqueta && (
        <rect
          x={p.x + 3}
          y={p.y + p.h * 0.34}
          width={p.w - 6}
          height="12"
          rx="1.5"
          fill="#fffaf0"
        />
      )}
    </g>
  );
}

/** Libro acostado (para pilas). */
function Acostado({ x, y, w, h, color }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="2" fill={color} />
      <rect x={x + w - 8} y={y + 2} width="6" height={h - 4} rx="1" fill="#fffaf0" />
    </g>
  );
}

/** Planta en maceta. */
function Planta({ x, y, escala = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${escala})`}>
      <ellipse cx="-12" cy="-30" rx="7" ry="16" transform="rotate(-30 -12 -30)" fill="#6a994e" />
      <ellipse cx="12" cy="-32" rx="7" ry="17" transform="rotate(28 12 -32)" fill="#8ab17d" />
      <ellipse cx="0" cy="-38" rx="7" ry="19" fill="#6a994e" />
      <ellipse cx="-4" cy="-22" rx="6" ry="12" transform="rotate(-55 -4 -22)" fill="#8ab17d" />
      <path d="M-15 -14h30l-4 22h-22z" fill="#d17a54" />
      <rect x="-17" y="-16" width="34" height="6" rx="2" fill="#e08b63" />
    </g>
  );
}

/** Libro abierto en el aire, como un pájaro. */
function Volando({ x, y, giro, color, demora }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${giro})`}>
      <g className={estilos.flota} style={{ animationDelay: demora }}>
        <path d="M40 34 L2 22 L8 0 L40 12 Z" fill={color} />
        <path d="M40 34 L78 22 L72 0 L40 12 Z" fill={color} />
        <path d="M40 30 L7 19 L12 4 L40 15 Z" fill="#fffaf0" />
        <path d="M40 30 L73 19 L68 4 L40 15 Z" fill="#f4ecd9" />
        <path
          d="M16 10l18 6M15 16l18 6M64 10l-18 6M65 16l-18 6"
          stroke="#dcd0b8"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      </g>
    </g>
  );
}

/**
 * Ilustración del inicio: una biblioteca de madera clara con lomos variados, plantas, pilas y un
 * hueco del que salen volando libros abiertos y una hoja suelta. Es decorativa.
 */
export default function Biblioteca() {
  return (
    <svg className={estilos.lienzo} viewBox="0 0 520 440" aria-hidden="true" focusable="false">
      <ellipse cx="316" cy="420" rx="182" ry="9" fill="rgba(0,0,0,0.13)" />

      {/* Arriba del mueble: planta, pila y dos libros apoyados */}
      <Planta x={190} y={96} escala={1.1} />
      <Acostado x={262} y={84} w={70} h={12} color="#264653" />
      <Acostado x={266} y={72} w={62} h={12} color="#e9c46a" />
      <Acostado x={260} y={61} w={66} h={11} color="#e76f51" />
      <g transform="rotate(12 420 96)">
        <rect x="404" y="34" width="18" height="62" rx="2" fill="#5c7d9b" />
        <rect x="404" y="42" width="18" height="3" fill="rgba(255,255,255,0.55)" />
      </g>
      <rect x="384" y="40" width="20" height="56" rx="2" fill="#e5989b" />
      <rect x="384" y="48" width="20" height="3" fill="rgba(255,255,255,0.55)" />

      {/* Mueble */}
      <rect x="150" y="96" width="330" height="316" rx="8" fill={MADERA.marco} />
      <rect x="466" y="96" width="14" height="316" rx="6" fill={MADERA.sombra} />
      <rect x="166" y="112" width="298" height="282" fill={MADERA.fondo} />
      {[175, 248, 321].map((y) => (
        <g key={y}>
          <rect x="166" y={y} width="298" height="10" fill={MADERA.tabla} />
          <rect x="166" y={y + 7} width="298" height="3" fill={MADERA.sombra} />
        </g>
      ))}

      {/* Lomos */}
      {TRAMOS.flat().map((p, n) => (
        <Lomo key={n} p={p} />
      ))}
      {/* Estante 1: planta al final */}
      <Planta x={442} y={175} escala={0.85} />
      {/* Estante 2: un libro apoyado en el hueco */}
      <g transform={`rotate(-14 ${392} ${piso(1)})`}>
        <rect x="374" y={piso(1) - 56} width="18" height="56" rx="2" fill="#e76f51" />
        <rect x="374" y={piso(1) - 49} width="18" height="2.5" fill="rgba(255,255,255,0.55)" />
      </g>
      {/* Estante 3: pila acostada al principio */}
      <Acostado x={172} y={piso(2) - 14} w={52} h={14} color="#2f4858" />
      <Acostado x={176} y={piso(2) - 26} w={46} h={12} color="#f4a261" />
      <Acostado x={170} y={piso(2) - 37} w={50} h={11} color="#8ab17d" />

      {/* Volando: dos libros abiertos y una hoja suelta */}
      <Volando x={36} y={150} giro={-14} color="#e76f51" demora="0s" />
      <Volando x={60} y={262} giro={12} color="#264653" demora="-2s" />
      <g transform="translate(96 214) rotate(-18)">
        <g className={estilos.flota} style={{ animationDelay: '-1s' }}>
          <rect x="0" y="0" width="30" height="38" rx="2" fill="#fffaf0" />
          <path
            d="M6 9h18M6 15h18M6 21h14"
            stroke="#dcd0b8"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </g>
      </g>
      <path
        d="M124 160c10-6 20-6 28 0M136 284c8-5 16-5 22 0"
        stroke="#ffffff"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
        opacity="0.75"
      />
    </svg>
  );
}
