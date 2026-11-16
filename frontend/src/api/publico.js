// Datos públicos: se piden sin sesión (no llevan token).
export async function obtenerInicioPublico(limite = 12) {
  const respuesta = await fetch(`/api/v1/publico/inicio?limite=${limite}`);
  if (!respuesta.ok) throw new Error(`El backend respondió ${respuesta.status}`);
  return respuesta.json();
}
