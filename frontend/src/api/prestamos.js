import { api } from './client.js';

export const listarPrestamos = (params) => api.get('/prestamos', params);
export const obtenerPrestamo = (id) => api.get(`/prestamos/${id}`);
export const registrarPrestamo = (datos) => api.post('/prestamos', datos);
export const entregarPrestamo = (id) => api.post(`/prestamos/${id}/entregar`);
export const renovarPrestamo = (id) => api.post(`/prestamos/${id}/renovar`);
export const cancelarPrestamo = (id, motivo) => api.post(`/prestamos/${id}/cancelar`, { motivo });
export const detectarVencidos = () => api.post('/admin/tareas/detectar-vencidos');

export const listarParametros = () => api.get('/parametros');
export const actualizarParametro = (clave, valor) => api.put(`/parametros/${clave}`, { valor });
