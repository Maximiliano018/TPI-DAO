// Consulta el estado del backend. En desarrollo, Vite redirige /api al puerto 8000.
export async function obtenerVersionBackend() {
  const respuesta = await fetch('/api/version');
  if (!respuesta.ok) {
    throw new Error(`El backend respondió ${respuesta.status}`);
  }
  return respuesta.json();
}
