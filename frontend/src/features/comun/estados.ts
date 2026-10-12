// Texto y color de cada estado, según DESIGN-SYSTEM.md §3 "Mapeo de estados a color".
import type { VarianteBadge } from '../../components/Badge/Badge'

type Mapeo = Record<string, { texto: string; variante: VarianteBadge }>

export const ESTADOS = {
  remito: {
    GENERADO: { texto: 'Generado', variante: 'neutral' },
    EMPAQUETADO: { texto: 'Empaquetado', variante: 'neutral' },
    EN_TRANSITO: { texto: 'En tránsito', variante: 'info' },
    RECIBIDO: { texto: 'Recibido', variante: 'exito' },
    EXTRAVIADO: { texto: 'Extraviado', variante: 'peligro' },
    CANCELADO: { texto: 'Cancelado', variante: 'neutral' },
  },
  revision: {
    CONFORME: { texto: 'Conforme', variante: 'exito' },
    DANADO: { texto: 'Dañado', variante: 'advertencia' },
    DESTRUIDO: { texto: 'Destruido', variante: 'peligro' },
  },
  prestamo: {
    EN_ENVIO: { texto: 'En envío', variante: 'info' },
    LISTO_PARA_RETIRO: { texto: 'Listo para retiro', variante: 'advertencia' },
    ACTIVO: { texto: 'Activo', variante: 'primario' },
    DEVUELTO: { texto: 'Devuelto', variante: 'exito' },
    CANCELADO: { texto: 'Cancelado', variante: 'neutral' },
  },
  ejemplar: {
    DISPONIBLE: { texto: 'Disponible', variante: 'exito' },
    RESERVADO: { texto: 'Reservado', variante: 'advertencia' },
    PENDIENTE_DESPACHO: { texto: 'Pendiente de despacho', variante: 'info' },
    EN_TRANSITO: { texto: 'En tránsito', variante: 'info' },
    PRESTADO: { texto: 'Prestado', variante: 'primario' },
    EN_REVISION: { texto: 'En revisión', variante: 'advertencia' },
    BAJA: { texto: 'Baja', variante: 'peligro' },
  },
  condicion: {
    BUENA: { texto: 'Buena', variante: 'exito' },
    REGULAR: { texto: 'Regular', variante: 'advertencia' },
    DANADA: { texto: 'Dañada', variante: 'peligro' },
  },
  reserva: {
    PENDIENTE: { texto: 'Pendiente', variante: 'neutral' },
    ASIGNADA: { texto: 'Asignada', variante: 'advertencia' },
    CUMPLIDA: { texto: 'Cumplida', variante: 'exito' },
    VENCIDA: { texto: 'Vencida', variante: 'peligro' },
    CANCELADA: { texto: 'Cancelada', variante: 'neutral' },
  },
  multa: {
    PENDIENTE: { texto: 'Pendiente', variante: 'peligro' },
    SALDADA: { texto: 'Saldada', variante: 'exito' },
  },
} satisfies Record<string, Mapeo>

export type Entidad = keyof typeof ESTADOS
