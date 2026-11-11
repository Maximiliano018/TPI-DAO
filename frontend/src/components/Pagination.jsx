import Button from './Button.jsx';
import estilos from './Pagination.module.css';

const TAMANOS = [10, 20, 50];

/** Paginación con anterior/siguiente, tamaño de página y total. */
export default function Pagination({ page, size, total, onPage, onSize }) {
  const paginas = Math.max(1, Math.ceil(total / size));
  const desde = total === 0 ? 0 : (page - 1) * size + 1;
  const hasta = Math.min(page * size, total);
  return (
    <nav className={estilos.paginacion} aria-label="Paginación">
      <p className={estilos.total} aria-live="polite">
        {total === 0 ? 'Sin resultados' : `${desde}–${hasta} de ${total}`}
      </p>
      {onSize && (
        <label className={estilos.tamano}>
          Por página
          <select value={size} onChange={(e) => onSize(Number(e.target.value))}>
            {TAMANOS.map((tamano) => (
              <option key={tamano} value={tamano}>
                {tamano}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className={estilos.botones}>
        <Button
          variante="secondary"
          tamano="sm"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          Anterior
        </Button>
        <span aria-current="page">
          Página {page} de {paginas}
        </span>
        <Button
          variante="secondary"
          tamano="sm"
          disabled={page >= paginas}
          onClick={() => onPage(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  );
}
