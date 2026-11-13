import { PERMISOS } from '../utils/roles.js';

/**
 * Ítems del menú lateral. Cada módulo agrega el suyo cuando existe: los que todavía no tienen
 * pantalla no se muestran. `permiso` limita el ítem a quien lo tenga.
 */
export const ITEMS_DE_MENU = [
  { to: '/', texto: 'Inicio', fin: true },
  { to: '/sedes', texto: 'Sedes' },
  { to: '/socios', texto: 'Socios', permiso: PERMISOS.SOCIO_LEER },
  { to: '/mis-datos', texto: 'Mis datos', permiso: PERMISOS.SOCIO_VER_PROPIO },
  { to: '/usuarios', texto: 'Usuarios', permiso: PERMISOS.USUARIO_ADMINISTRAR },
];
