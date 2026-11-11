import { useEffect, useState } from 'react';
import Button from './Button.jsx';
import estilos from './FilterBar.module.css';

/**
 * Búsqueda con espera (300 ms) para filtros de listados. El texto se mantiene local mientras se
 * escribe y recién después se informa con `onBuscar`, para no consultar en cada tecla.
 */
export function BusquedaConEspera({ etiqueta, valor, onBuscar, esperaMs = 300 }) {
  const [texto, setTexto] = useState(valor ?? '');

  useEffect(() => setTexto(valor ?? ''), [valor]);
  useEffect(() => {
    if (texto === (valor ?? '')) return undefined;
    const temporizador = setTimeout(() => onBuscar(texto), esperaMs);
    return () => clearTimeout(temporizador);
  }, [texto, valor, onBuscar, esperaMs]);

  return (
    <label className={estilos.campo}>
      <span className={estilos.etiqueta}>{etiqueta}</span>
      <input
        type="search"
        className={estilos.control}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
    </label>
  );
}

/** Selector nativo para un filtro. */
export function FiltroSelect({ etiqueta, valor, onCambiar, children }) {
  return (
    <label className={estilos.campo}>
      <span className={estilos.etiqueta}>{etiqueta}</span>
      <select className={estilos.control} value={valor} onChange={(e) => onCambiar(e.target.value)}>
        {children}
      </select>
    </label>
  );
}

/** Contenedor de filtros con el botón «Limpiar». */
export default function FilterBar({ etiqueta, onLimpiar, hayFiltros = true, children }) {
  return (
    <form
      role="search"
      aria-label={etiqueta}
      className={estilos.barra}
      onSubmit={(e) => e.preventDefault()}
    >
      {children}
      {hayFiltros && (
        <Button variante="secondary" onClick={onLimpiar}>
          Limpiar filtros
        </Button>
      )}
    </form>
  );
}
