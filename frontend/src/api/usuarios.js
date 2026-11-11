import { api } from './client.js';

export const listarUsuarios = (params) => api.get('/usuarios', params);
export const obtenerUsuario = (id) => api.get(`/usuarios/${id}`);
export const crearUsuario = (datos) => api.post('/usuarios', datos);
export const modificarUsuario = (id, datos) => api.put(`/usuarios/${id}`, datos);
export const darDeBajaUsuario = (id) => api.post(`/usuarios/${id}/baja`);
export const reactivarUsuario = (id) => api.post(`/usuarios/${id}/reactivar`);
