import { PERMISOS, operaEn } from '../../utils/roles.js';

const ACTIVAS = ['PENDIENTE', 'DISPONIBLE_PARA_RETIRO'];

/**
 * La cancela el socio (la propia) o el personal que opera en la sede de retiro: el bibliotecario
 * de esa sede o el administrador. El backend lo vuelve a validar.
 */
export function puedeCancelar(reserva, usuario, tienePermiso) {
  if (!ACTIVAS.includes(reserva.estado)) return false;
  if (tienePermiso(PERMISOS.RESERVA_PROPIA)) return usuario.socio_id === reserva.socio_id;
  return tienePermiso(PERMISOS.RESERVA_REGISTRAR) && operaEn(usuario, reserva.sede_retiro_id);
}

/** La entrega el personal de la sede de retiro (o el administrador), con el ejemplar asignado. */
export function puedeEntregar(reserva, usuario, tienePermiso) {
  return (
    reserva.estado === 'DISPONIBLE_PARA_RETIRO' &&
    tienePermiso(PERMISOS.RESERVA_REGISTRAR) &&
    operaEn(usuario, reserva.sede_retiro_id)
  );
}
