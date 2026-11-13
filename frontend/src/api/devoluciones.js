import { api } from './client.js';

export const registrarDevolucion = (prestamoId, datos) =>
  api.post(`/prestamos/${prestamoId}/devolucion`, datos);
export const listarMultas = (params) => api.get('/multas', params);
export const saldarMulta = (id) => api.post(`/multas/${id}/saldar`);
