import { api } from './client.js';

export const listarSocios = (params) => api.get('/socios', params);
export const buscarPosiblesDuplicados = (params) => api.get('/socios/posibles-duplicados', params);
export const obtenerSocio = (id) => api.get(`/socios/${id}`);
export const crearSocio = (datos) => api.post('/socios', datos);
export const modificarSocio = (id, datos) => api.put(`/socios/${id}`, datos);
export const inhabilitarSocio = (id, motivo) => api.post(`/socios/${id}/inhabilitar`, { motivo });
export const rehabilitarSocio = (id) => api.post(`/socios/${id}/rehabilitar`);
export const darDeBajaSocio = (id, tipo, motivo) =>
  api.post(`/socios/${id}/baja`, { tipo, motivo });
export const reactivarSocio = (id) => api.post(`/socios/${id}/reactivar`);
export const crearCuentaSocio = (id, datos) => api.post(`/socios/${id}/cuenta`, datos);
export const solicitarReactivacion = (id, mensaje) =>
  api.post(`/socios/${id}/solicitud-reactivacion`, { mensaje });
export const aprobarSolicitud = (id) => api.post(`/socios/${id}/solicitud-reactivacion/aprobar`);
export const rechazarSolicitud = (id, motivo) =>
  api.post(`/socios/${id}/solicitud-reactivacion/rechazar`, { motivo });
export const historialSocio = (id, params) => api.get(`/socios/${id}/historial`, params);
