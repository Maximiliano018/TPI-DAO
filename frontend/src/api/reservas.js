import { api } from './client.js';

export const listarReservas = (params) => api.get('/reservas', params);
export const obtenerReserva = (id) => api.get(`/reservas/${id}`);
export const crearReserva = (datos) => api.post('/reservas', datos);
export const cancelarReserva = ({ id, motivo }) =>
  api.post(`/reservas/${id}/cancelar`, motivo ? { motivo } : {});
export const retirarReserva = (id) => api.post(`/reservas/${id}/retirar`);
export const vencerReservas = () => api.post('/admin/tareas/vencer-reservas');
