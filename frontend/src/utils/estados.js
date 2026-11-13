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
  socio: {
    HABILITADO: { tono: 'success', texto: 'Habilitado' },
    INHABILITADO: { tono: 'danger', texto: 'Inhabilitado' },
    BAJA: { tono: 'neutral', texto: 'Dado de baja' },
  },
};

/** Causa de inhabilitación de un socio, para mostrar. */
export const MOTIVOS_DE_INHABILITACION = {
  ADMINISTRATIVA: 'Decisión administrativa',
  PRESTAMO_VENCIDO: 'Préstamo vencido',
  MULTA_IMPAGA: 'Multa impaga',
};

/** Etiqueta de un estado; si no está en el mapa se muestra el valor tal cual. */
export function estadoDe(entidad, estado) {
  return ESTADOS[entidad]?.[estado] ?? { tono: 'neutral', texto: String(estado) };
}
