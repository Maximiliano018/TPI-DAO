import { PERMISOS } from '../../utils/roles.js';

const ACTIVAS = ['PENDIENTE', 'DISPONIBLE_PARA_RETIRO'];

/**
 * La cancela el socio (la propia) o el bibliotecario de la sede de retiro; el administrador
 * solo consulta. El backend lo vuelve a validar.
 */
export function puedeCancelar(reserva, usuario, tienePermiso) {
  if (!ACTIVAS.includes(reserva.estado)) return false;
  if (tienePermiso(PERMISOS.RESERVA_PROPIA)) return usuario.socio_id === reserva.socio_id;
  return tienePermiso(PERMISOS.RESERVA_REGISTRAR) && usuario.sede_id === reserva.sede_retiro_id;
}

/** La entrega el bibliotecario de la sede de retiro, con el ejemplar ya asignado. */
export function puedeEntregar(reserva, usuario, tienePermiso) {
  return (
    reserva.estado === 'DISPONIBLE_PARA_RETIRO' &&
    tienePermiso(PERMISOS.RESERVA_REGISTRAR) &&
    usuario.sede_id === reserva.sede_retiro_id
  );
}
