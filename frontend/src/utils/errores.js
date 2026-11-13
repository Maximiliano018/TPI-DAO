// Código de error del backend → mensaje para la persona usuaria.
// Si un código no está, se muestra el `mensaje` que envía el backend.
export const MENSAJES_DE_ERROR = {
  CREDENCIALES_INVALIDAS: 'Usuario o contraseña incorrectos',
  TOKEN_INVALIDO: 'Su sesión venció. Ingrese de nuevo.',
  FORBIDDEN: 'No tiene permiso para realizar esta acción.',
  SEDE_CODIGO_DUPLICADO: 'Ya existe una sede con ese código',
  SEDE_NOMBRE_DUPLICADO: 'Ya existe una sede con ese nombre',
  SEDE_EN_BAJA: 'La sede está dada de baja. Reactívela para continuar',
  SEDE_YA_EN_BAJA: 'La sede ya estaba en ese estado. Se actualizó la pantalla',
  SEDE_YA_ACTIVA: 'La sede ya estaba en ese estado. Se actualizó la pantalla',
  SEDE_NO_ENCONTRADA: 'La sede solicitada no existe o no está disponible',
  HORARIO_INVALIDO:
    'Revise los horarios: las franjas no pueden solaparse y el cierre debe ser posterior a la apertura',
  EXCEPCION_HORARIO_SUPERPUESTA: 'Ya hay un cierre cargado para esa fecha y horario',
  EXCEPCION_HORARIO_INVALIDA: 'Revise la fecha y las horas del cierre',
  EXCEPCION_HORARIO_NO_ENCONTRADA: 'El cierre ya no existe. Se actualizó la pantalla',
  LOCALIDAD_INVALIDA: 'Elija una localidad de la lista',
  CONFLICTO_DE_VERSION: 'Otra persona modificó la sede. Recargue para ver los cambios',
  DUPLICADO: 'Ya existe un usuario con ese nombre de usuario',
  USUARIO_NO_ENCONTRADO: 'El usuario solicitado no existe',
  USUARIO_YA_EN_BAJA: 'El usuario ya estaba dado de baja. Se actualizó la pantalla',
  USUARIO_YA_ACTIVO: 'El usuario ya estaba activo. Se actualizó la pantalla',
  SOCIO_NO_ENCONTRADO: 'El socio solicitado no existe',
  SOCIO_EN_BAJA: 'El socio está dado de baja. Reactívelo para continuar',
  SOCIO_YA_EN_BAJA: 'El socio ya estaba dado de baja. Se actualizó la pantalla',
  SOCIO_YA_ACTIVO: 'El socio no estaba dado de baja. Se actualizó la pantalla',
  SOCIO_YA_HABILITADO: 'El socio ya estaba habilitado. Se actualizó la pantalla',
  SOCIO_YA_INHABILITADO: 'El socio ya estaba inhabilitado por decisión administrativa',
  SOCIO_CON_CUENTA: 'El socio ya tiene una cuenta de acceso',
  LIBRO_NO_ENCONTRADO: 'El libro solicitado no existe',
  EJEMPLAR_NO_ENCONTRADO: 'El ejemplar solicitado no existe',
  EJEMPLAR_CODIGO_DUPLICADO: 'Ya existe un ejemplar con ese código de inventario en la red',
  CATEGORIA_INVALIDA: 'Elija una categoría de la lista',
  TRANSICION_INVALIDA: 'La operación no corresponde al estado actual. Se actualizó la pantalla',
  PRESTAMO_NO_ENCONTRADO: 'El préstamo solicitado no existe',
  REMITO_NO_ENCONTRADO: 'El remito solicitado no existe',
};

// Códigos cuyo mensaje del servidor es más preciso que uno fijo (traen el socio o la causa).
const USAR_MENSAJE_DEL_SERVIDOR = new Set([
  'POSIBLE_DUPLICADO',
  'SOCIO_CON_CAUSAS_VIGENTES',
  'SOCIO_CON_ACTIVIDAD_PENDIENTE',
  'SOCIO_INHABILITADO',
  'LIBRO_DUPLICADO',
  'LIBRO_CON_EJEMPLARES',
  'EJEMPLAR_NO_DISPONIBLE',
  'LIMITE_PRESTAMOS',
  'LIBRO_REPETIDO',
  'RENOVACION_NO_PERMITIDA',
  'EJEMPLAR_NO_RECIBIDO',
  'EJEMPLAR_EN_OTRO_REMITO',
  'EJEMPLAR_FUERA_DE_SEDE_ORIGEN',
  'PLAZO_DE_TRANSITO_VIGENTE',
  'REMITO_INVALIDO',
  'SEDE_CON_ACTIVIDAD_PENDIENTE',
]);

/** Mensaje a mostrar para un `ApiError` (o cualquier error). */
export function mensajeDeError(error) {
  if (!error) return '';
  if (USAR_MENSAJE_DEL_SERVIDOR.has(error.codigo) && error.mensaje) return error.mensaje;
  // La transición inválida trae el estado actual en el mensaje del servidor.
  if (error.codigo === 'TRANSICION_INVALIDA' && error.mensaje) return error.mensaje;
  if (error.codigo && MENSAJES_DE_ERROR[error.codigo]) return MENSAJES_DE_ERROR[error.codigo];
  return error.mensaje || error.message || 'Ocurrió un error inesperado. Reintente.';
}

/** Errores por campo del servidor: `{ campo: problema }` a partir de `detalles[]`. */
export function erroresPorCampo(error) {
  const campos = {};
  for (const detalle of error?.detalles ?? []) {
    if (detalle?.campo && detalle?.problema && !campos[detalle.campo]) {
      campos[detalle.campo] = detalle.problema;
    }
  }
  return campos;
}
