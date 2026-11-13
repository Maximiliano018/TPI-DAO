import { api } from './client.js';

export const listarSocios = (params) => api.get('/socios', params);
export const buscarPosiblesDuplicados = (params) => api.get('/socios/posibles-duplicados', params);
export const obtenerSocio = (id) => api.get(`/socios/${id}`);
export const crearSocio = (datos) => api.post('/socios', datos);
export const modificarSocio = (id, datos) => api.put(`/socios/${id}`, datos);
export const inhabilitarSocio = (id, motivo) => api.post(`/socios/${id}/inhabilitar`, { motivo });
export const rehabilitarSocio = (id) => api.post(`/socios/${id}/rehabilitar`);
export const darDeBajaSocio = (id, motivo) => api.post(`/socios/${id}/baja`, { motivo });
export const reactivarSocio = (id) => api.post(`/socios/${id}/reactivar`);
export const crearCuentaSocio = (id, datos) => api.post(`/socios/${id}/cuenta`, datos);
