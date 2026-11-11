// Única tabla de correspondencia estado → etiqueta (tono y texto). Ver guía de estilos.
export const ESTADOS = {
  sede: {
    ACTIVA: { tono: 'success', texto: 'Activa' },
    BAJA: { tono: 'neutral', texto: 'Baja' },
  },
  usuario: {
    ACTIVO: { tono: 'success', texto: 'Activo' },
    BAJA: { tono: 'neutral', texto: 'Dado de baja' },
  },
};

/** Etiqueta de un estado; si no está en el mapa se muestra el valor tal cual. */
export function estadoDe(entidad, estado) {
  return ESTADOS[entidad]?.[estado] ?? { tono: 'neutral', texto: String(estado) };
}
