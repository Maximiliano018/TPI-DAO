import { api } from './client.js';

export const listarSedes = (params) => api.get('/sedes', params);
export const resumenSedes = () => api.get('/sedes/resumen');
export const obtenerSede = (id) => api.get(`/sedes/${id}`);
export const crearSede = (datos) => api.post('/sedes', datos);
export const modificarSede = (id, datos) => api.put(`/sedes/${id}`, datos);
export const darDeBajaSede = (id, datos) => api.post(`/sedes/${id}/baja`, datos);
export const reactivarSede = (id, datos) => api.post(`/sedes/${id}/reactivar`, datos);
export const listarExcepciones = (id, params) =>
  api.get(`/sedes/${id}/excepciones-horario`, params);
export const agregarExcepcion = (id, datos) => api.post(`/sedes/${id}/excepciones-horario`, datos);
export const quitarExcepcion = (id, excepcionId) =>
  api.delete(`/sedes/${id}/excepciones-horario/${excepcionId}`);
export const historialSede = (id, params) => api.get(`/sedes/${id}/historial`, params);
export const listarLocalidades = (params) => api.get('/localidades', params);
export const listarProvincias = () => api.get('/provincias');
