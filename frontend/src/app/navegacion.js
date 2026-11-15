import { PERMISOS } from '../utils/roles.js';

/**
 * Secciones del menú lateral. Cada sección es una pila de libros sobre su propia tabla, con una
 * cartela que la nombra; solo se muestra si la persona puede ver alguno de sus ítems. `permiso`
 * limita el ítem a quien lo tenga (el personal ve «Préstamos»; el socio, «Mis préstamos»).
 */
export const SECCIONES_DE_MENU = [
  { titulo: null, items: [{ to: '/', texto: 'Inicio', fin: true }] },
  {
    titulo: 'Circulación',
    items: [
      { to: '/prestamos', texto: 'Préstamos', permiso: PERMISOS.PRESTAMO_LEER },
      { to: '/prestamos', texto: 'Mis préstamos', permiso: PERMISOS.PRESTAMO_VER_PROPIOS },
      { to: '/reservas', texto: 'Reservas', permiso: PERMISOS.RESERVA_LEER },
      { to: '/reservas', texto: 'Mis reservas', permiso: PERMISOS.RESERVA_PROPIA },
      { to: '/remitos', texto: 'Remitos', permiso: PERMISOS.REMITO_LEER },
      { to: '/multas', texto: 'Multas', permiso: PERMISOS.MULTA_LEER },
      { to: '/multas', texto: 'Mis multas', permiso: PERMISOS.MULTA_VER_PROPIAS },
    ],
  },
  {
    titulo: 'Colección',
    items: [
      { to: '/catalogo', texto: 'Catálogo', permiso: PERMISOS.CATALOGO_LEER },
      { to: '/ejemplares', texto: 'Ejemplares', permiso: PERMISOS.EJEMPLAR_LEER },
    ],
  },
  {
    titulo: 'Red y socios',
    items: [
      { to: '/sedes', texto: 'Sedes' },
      { to: '/socios', texto: 'Socios', permiso: PERMISOS.SOCIO_LEER },
      { to: '/mis-datos', texto: 'Mis datos', permiso: PERMISOS.SOCIO_VER_PROPIO },
    ],
  },
  {
    titulo: 'Gestión',
    items: [
      { to: '/reportes', texto: 'Reportes', permiso: PERMISOS.CATALOGO_LEER },
      { to: '/usuarios', texto: 'Usuarios', permiso: PERMISOS.USUARIO_ADMINISTRAR },
      { to: '/parametros', texto: 'Parámetros', permiso: PERMISOS.PARAMETROS_ADMINISTRAR },
    ],
  },
];

/** Todos los ítems en orden, sin secciones. */
export const ITEMS_DE_MENU = SECCIONES_DE_MENU.flatMap((seccion) => seccion.items);
