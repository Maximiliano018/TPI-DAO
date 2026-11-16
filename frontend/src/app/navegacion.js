import { PERMISOS } from '../utils/roles.js';

/**
 * Secciones del menú lateral. Cada sección tiene un nombre, el color de su franja (`franja`, uno
 * de los colores de lomo) y sus opciones con su ícono (ver `components/Icono.jsx`); solo se muestra
 * si la persona puede ver alguna. `permiso` limita la opción a quien lo tenga (el personal ve
 * «Préstamos»; el socio, «Mis préstamos»).
 */
export const SECCIONES_DE_MENU = [
  {
    titulo: null,
    franja: 'amarillo',
    items: [{ to: '/', texto: 'Inicio', icono: 'inicio', fin: true }],
  },
  {
    titulo: 'Circulación',
    franja: 'rojo',
    items: [
      { to: '/prestamos', texto: 'Préstamos', icono: 'libro', permiso: PERMISOS.PRESTAMO_LEER },
      {
        to: '/prestamos',
        texto: 'Mis préstamos',
        icono: 'libro',
        permiso: PERMISOS.PRESTAMO_VER_PROPIOS,
      },
      { to: '/reservas', texto: 'Reservas', icono: 'reservar', permiso: PERMISOS.RESERVA_LEER },
      {
        to: '/reservas',
        texto: 'Mis reservas',
        icono: 'reservar',
        permiso: PERMISOS.RESERVA_PROPIA,
      },
      { to: '/multas', texto: 'Multas', icono: 'comprobante', permiso: PERMISOS.MULTA_LEER },
      {
        to: '/multas',
        texto: 'Mis multas',
        icono: 'comprobante',
        permiso: PERMISOS.MULTA_VER_PROPIAS,
      },
    ],
  },
  {
    titulo: 'Logística',
    franja: 'naranja',
    items: [{ to: '/remitos', texto: 'Remitos', icono: 'camion', permiso: PERMISOS.REMITO_LEER }],
  },
  {
    titulo: 'Colección',
    franja: 'verde',
    items: [
      { to: '/catalogo', texto: 'Catálogo', icono: 'biblioteca', permiso: PERMISOS.CATALOGO_LEER },
      { to: '/ejemplares', texto: 'Ejemplares', icono: 'codigo', permiso: PERMISOS.EJEMPLAR_LEER },
    ],
  },
  {
    titulo: 'Red y socios',
    franja: 'azul',
    items: [
      { to: '/sedes', texto: 'Sedes', icono: 'edificio' },
      { to: '/socios', texto: 'Socios', icono: 'personas', permiso: PERMISOS.SOCIO_LEER },
      {
        to: '/mis-datos',
        texto: 'Mis datos',
        icono: 'persona',
        permiso: PERMISOS.SOCIO_VER_PROPIO,
      },
    ],
  },
  {
    titulo: 'Gestión',
    franja: 'violeta',
    items: [
      { to: '/reportes', texto: 'Reportes', icono: 'grafico', permiso: PERMISOS.CATALOGO_LEER },
      {
        to: '/usuarios',
        texto: 'Usuarios',
        icono: 'personal',
        permiso: PERMISOS.USUARIO_ADMINISTRAR,
      },
      {
        to: '/parametros',
        texto: 'Parámetros',
        icono: 'ajustes',
        permiso: PERMISOS.PARAMETROS_ADMINISTRAR,
      },
    ],
  },
];

/** Todos los ítems en orden, sin secciones. */
export const ITEMS_DE_MENU = SECCIONES_DE_MENU.flatMap((seccion) => seccion.items);
