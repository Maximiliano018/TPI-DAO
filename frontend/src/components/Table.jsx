import estilos from './Table.module.css';

/**
 * Tabla accesible con orden por columna. Bajo 768 px se muestra como tarjetas (cada celda
 * conserva su título en `data-label`).
 *
 * @param {{
 *   etiqueta: string,
 *   columnas: {clave: string, titulo: string, render?: (fila: object) => import('react').ReactNode, orden?: string}[],
 *   filas: object[],
 *   idDe: (fila: object) => string|number,
 *   orden?: string,
 *   onOrden?: (orden: string) => void,
 * }} props
 */
export default function Table({ etiqueta, columnas, filas, idDe, orden, onOrden }) {
  const campoOrden = orden?.replace(/^-/, '');
  const descendente = orden?.startsWith('-');
  return (
    <div className={estilos.contenedor}>
      <table className={estilos.tabla}>
        <caption className="sr-only">{etiqueta}</caption>
        <thead>
          <tr>
            {columnas.map((columna) => {
              const ordenable = Boolean(columna.orden && onOrden);
              const activa = ordenable && columna.orden === campoOrden;
              return (
                <th
                  key={columna.clave}
                  scope="col"
                  aria-sort={activa ? (descendente ? 'descending' : 'ascending') : undefined}
                >
                  {ordenable ? (
                    <button
                      type="button"
                      className={estilos.ordenar}
                      onClick={() =>
                        onOrden(activa && !descendente ? `-${columna.orden}` : columna.orden)
                      }
                    >
                      {columna.titulo}
                      <span aria-hidden="true">{activa ? (descendente ? ' ▼' : ' ▲') : ''}</span>
                    </button>
                  ) : (
                    columna.titulo
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={idDe(fila)}>
              {columnas.map((columna) => (
                <td key={columna.clave} data-label={columna.titulo}>
                  {columna.render ? columna.render(fila) : fila[columna.clave]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
