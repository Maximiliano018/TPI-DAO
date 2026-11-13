import { PERMISOS } from '../utils/roles.js';

/**
 * Ítems del menú lateral. Cada módulo agrega el suyo cuando existe: los que todavía no tienen
 * pantalla no se muestran. `permiso` limita el ítem a quien lo tenga.
 */
export const ITEMS_DE_MENU = [
  { to: '/', texto: 'Inicio', fin: true },
  { to: '/sedes', texto: 'Sedes' },
  { to: '/catalogo', texto: 'Catálogo', permiso: PERMISOS.CATALOGO_LEER },
  { to: '/ejemplares', texto: 'Ejemplares', permiso: PERMISOS.EJEMPLAR_LEER },
  { to: '/prestamos', texto: 'Préstamos', permiso: PERMISOS.PRESTAMO_LEER },
  { to: '/prestamos', texto: 'Mis préstamos', permiso: PERMISOS.PRESTAMO_VER_PROPIOS },
  { to: '/reservas', texto: 'Reservas', permiso: PERMISOS.RESERVA_LEER },
  { to: '/reservas', texto: 'Mis reservas', permiso: PERMISOS.RESERVA_PROPIA },
  { to: '/remitos', texto: 'Remitos', permiso: PERMISOS.REMITO_LEER },
  { to: '/multas', texto: 'Multas', permiso: PERMISOS.MULTA_LEER },
  { to: '/multas', texto: 'Mis multas', permiso: PERMISOS.MULTA_VER_PROPIAS },
  { to: '/socios', texto: 'Socios', permiso: PERMISOS.SOCIO_LEER },
  { to: '/mis-datos', texto: 'Mis datos', permiso: PERMISOS.SOCIO_VER_PROPIO },
  { to: '/usuarios', texto: 'Usuarios', permiso: PERMISOS.USUARIO_ADMINISTRAR },
  { to: '/parametros', texto: 'Parámetros', permiso: PERMISOS.PARAMETROS_ADMINISTRAR },
];
