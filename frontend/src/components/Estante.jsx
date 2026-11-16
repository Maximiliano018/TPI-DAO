import estilos from './Estante.module.css';

// Colores de lomo en orden y el tono del texto que se lee sobre cada uno.
const LOMOS = [
  ['rosa', 'tinta'],
  ['negro', 'clara'],
  ['ocre', 'tinta'],
  ['marino', 'clara'],
  ['crema', 'tinta'],
  ['ciruela', 'clara'],
  ['bosque', 'clara'],
  ['burdeos', 'clara'],
  ['petroleo', 'tinta'],
];

/**
 * Estante decorativo: los títulos como lomos de pie, de colores planos y alturas distintas, sobre
 * una tabla. Es decorativo (los títulos se leen en la lista de más pedidos).
 *
 * @param {{titulos: string[], max?: number}} props
 */
export default function Estante({ titulos, max = 12 }) {
  return (
    <div className={estilos.estante} aria-hidden="true">
      <div className={estilos.lomos}>
        {titulos.slice(0, max).map((titulo, i) => {
          const [color, tinta] = LOMOS[i % LOMOS.length];
          return (
            <span
              key={`${titulo}-${i}`}
              className={estilos.lomo}
              style={{
                '--c': `var(--lomo-${color})`,
                '--t': tinta === 'tinta' ? 'var(--color-ink)' : '#fff',
                '--alto': `${Math.min(300, Math.max(190, 120 + titulo.length * 8 + ((i * 23) % 40)))}px`,
                '--ancho': `${58 + ((i * 17) % 26)}px`,
              }}
            >
              <span className={estilos.texto}>{titulo}</span>
            </span>
          );
        })}
      </div>
      <div className={estilos.tabla} />
    </div>
  );
}
