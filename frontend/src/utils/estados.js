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
  ejemplar: {
    DISPONIBLE: { tono: 'success', texto: 'Disponible' },
    APARTADO: { tono: 'info', texto: 'Apartado' },
    RESERVADO: { tono: 'info', texto: 'Reservado' },
    PRESTADO: { tono: 'warning', texto: 'Prestado' },
    EN_TRANSITO: { tono: 'info', texto: 'En tránsito' },
    EN_REVISION: { tono: 'danger', texto: 'En revisión' },
    BAJA: { tono: 'neutral', texto: 'Dado de baja' },
  },
  prestamo: {
    SOLICITADO: { tono: 'info', texto: 'Solicitado' },
    EN_ENVIO: { tono: 'info', texto: 'En envío' },
    ACTIVO: { tono: 'success', texto: 'Activo' },
    VENCIDO: { tono: 'danger', texto: 'Vencido' },
    DEVUELTO: { tono: 'neutral', texto: 'Devuelto' },
    CANCELADO: { tono: 'neutral', texto: 'Cancelado' },
  },
  remito: {
    GENERADO: { tono: 'info', texto: 'Generado' },
    EMPAQUETADO: { tono: 'info', texto: 'Empaquetado' },
    DESPACHADO: { tono: 'warning', texto: 'Despachado' },
    EN_TRANSITO: { tono: 'warning', texto: 'En tránsito' },
    RECIBIDO: { tono: 'success', texto: 'Recibido' },
    EXTRAVIADO: { tono: 'danger', texto: 'Extraviado' },
    DANADO: { tono: 'danger', texto: 'Recibido con daño' },
    DESTRUIDO: { tono: 'danger', texto: 'Recibido destruido' },
    ANULADO: { tono: 'neutral', texto: 'Anulado' },
  },
  reserva: {
    PENDIENTE: { tono: 'info', texto: 'En espera' },
    DISPONIBLE_PARA_RETIRO: { tono: 'success', texto: 'Lista para retirar' },
    CUMPLIDA: { tono: 'neutral', texto: 'Cumplida' },
    CANCELADA: { tono: 'neutral', texto: 'Cancelada' },
    VENCIDA: { tono: 'warning', texto: 'Vencida' },
  },
  multa: {
    PENDIENTE: { tono: 'danger', texto: 'Pendiente' },
    SALDADA: { tono: 'success', texto: 'Saldada' },
  },
};

export const TIPOS_DE_PRESTAMO = { LOCAL: 'Local', INTERBIBLIOTECARIO: 'Entre sedes' };
export const MOTIVOS_DE_REMITO = { ENVIO: 'Envío', RETORNO: 'Retorno', TRASLADO: 'Traslado' };

/** Estado físico de un ejemplar. */
export const ESTADOS_FISICOS = {
  NUEVO: 'Nuevo',
  BUENO: 'Bueno',
  REGULAR: 'Regular',
  DANADO: 'Dañado',
};

/** Cómo llegó el ejemplar en una devolución. */
export const ESTADOS_RECIBIDOS = {
  BUENO: 'Bueno',
  REGULAR: 'Regular',
  DANADO: 'Dañado',
  EXTRAVIADO: 'Extraviado (no lo entrega)',
};

/** Tipo de material del catálogo. */
export const TIPOS_DE_MATERIAL = {
  LIBRO: 'Libro',
  REVISTA: 'Revista',
  OBRA_DE_REFERENCIA: 'Obra de referencia',
  OTRO: 'Otro',
};

/** Causa de inhabilitación de un socio, para mostrar. */
export const MOTIVOS_DE_INHABILITACION = {
  ADMINISTRATIVA: 'Decisión administrativa',
  PRESTAMO_VENCIDO: 'Préstamo vencido',
  MULTA_IMPAGA: 'Multa impaga',
};

/** Tipos de baja de un socio, en orden de prioridad (la más grave primero). */
export const TIPOS_DE_BAJA = {
  FALLECIMIENTO: 'Fallecimiento',
  ADMINISTRATIVA: 'Administrativa (sanción)',
  A_PEDIDO: 'A pedido del socio',
};

/** Etiqueta de un estado; si no está en el mapa se muestra el valor tal cual. */
export function estadoDe(entidad, estado) {
  return ESTADOS[entidad]?.[estado] ?? { tono: 'neutral', texto: String(estado) };
}
