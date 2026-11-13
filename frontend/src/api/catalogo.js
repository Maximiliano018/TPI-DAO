import { api } from './client.js';

export const listarCategorias = () => api.get('/categorias');
export const buscarLibros = (params) => api.get('/libros', params);
export const obtenerLibro = (id) => api.get(`/libros/${id}`);
export const crearLibro = (datos) => api.post('/libros', datos);
export const modificarLibro = (id, datos) => api.put(`/libros/${id}`, datos);
export const eliminarLibro = (id) => api.delete(`/libros/${id}`);
export const obtenerDisponibilidad = (id) => api.get(`/libros/${id}/disponibilidad`);

export const listarEjemplares = (params) => api.get('/ejemplares', params);
export const obtenerEjemplar = (id) => api.get(`/ejemplares/${id}`);
export const crearEjemplar = (datos) => api.post('/ejemplares', datos);
export const modificarEjemplar = (id, datos) => api.put(`/ejemplares/${id}`, datos);
export const darDeBajaEjemplar = (id, datos) => api.post(`/ejemplares/${id}/baja`, datos);
export const repararEjemplar = (id, version) => api.post(`/ejemplares/${id}/reparado`, { version });
