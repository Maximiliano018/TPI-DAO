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
};

/** Mensaje a mostrar para un `ApiError` (o cualquier error). */
export function mensajeDeError(error) {
  if (!error) return '';
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
