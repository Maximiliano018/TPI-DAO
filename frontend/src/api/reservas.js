import { api } from './client.js';

export const listarReservas = (params) => api.get('/reservas', params);
export const crearReserva = (datos) => api.post('/reservas', datos);
export const cancelarReserva = (id) => api.post(`/reservas/${id}/cancelar`);
export const retirarReserva = (id) => api.post(`/reservas/${id}/retirar`);
export const vencerReservas = () => api.post('/admin/tareas/vencer-reservas');
