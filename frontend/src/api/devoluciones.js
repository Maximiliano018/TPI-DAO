import { api, descargar } from './client.js';

export const registrarDevolucion = (prestamoId, datos) =>
  api.post(`/prestamos/${prestamoId}/devolucion`, datos);
export const listarMultas = (params) => api.get('/multas', params);
export const saldarMulta = ({ id, medio, comprobante }) =>
  api.post(`/multas/${id}/saldar`, { medio, comprobante: comprobante || null });
export const iniciarPago = (multaId) => api.post(`/multas/${multaId}/pagos`);
export const obtenerPago = (id) => api.get(`/pagos/${id}`);
export const pagarEnLinea = ({ id, forma, tarjeta_ultimos4 }) =>
  api.post(`/pagos/${id}/pagar`, { forma, tarjeta_ultimos4 });
export const descargarComprobante = (id) => descargar(`/pagos/${id}/comprobante`);
