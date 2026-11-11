import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Filtros de un listado guardados en la URL (`?estado=ACTIVA&q=centro&page=2`), para compartir el
 * enlace y volver con «atrás». Cambiar un filtro reinicia la página.
 */
export function useFiltrosUrl() {
  const [params, setParams] = useSearchParams();

  const cambiar = useCallback(
    (cambios) => {
      setParams((previos) => {
        const nuevos = new URLSearchParams(previos);
        for (const [clave, valor] of Object.entries(cambios)) {
          if (valor === '' || valor === null || valor === undefined) nuevos.delete(clave);
          else nuevos.set(clave, String(valor));
        }
        if (!('page' in cambios)) nuevos.delete('page');
        return nuevos;
      });
    },
    [setParams],
  );
  const limpiar = useCallback(() => setParams({}), [setParams]);

  return {
    filtros: Object.fromEntries(params),
    cambiar,
    limpiar,
    hayFiltros: [...params.keys()].length > 0,
  };
}
