import { api } from './client.js';

export const listarRemitos = (params) => api.get('/remitos', params);
export const obtenerRemito = (id) => api.get(`/remitos/${id}`);
export const generarRemito = (datos) => api.post('/remitos', datos);
export const avanzarRemito = (id, accion) => api.post(`/remitos/${id}/${accion}`);
export const recibirRemito = (id, lineas) => api.post(`/remitos/${id}/recibir`, { lineas });
export const anularRemito = (id, motivo) => api.post(`/remitos/${id}/anular`, { motivo });
export const marcarExtraviado = (id, motivo) => api.post(`/remitos/${id}/extraviado`, { motivo });
