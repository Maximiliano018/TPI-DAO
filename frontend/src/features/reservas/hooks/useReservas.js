import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelarReserva,
  crearReserva,
  listarReservas,
  retirarReserva,
  vencerReservas,
} from '../../../api/reservas.js';

// Reservar, cancelar o retirar cambia ejemplares, préstamos y la situación del socio.
const AFECTADAS = [['reservas'], ['prestamos'], ['catalogo'], ['socios']];

export const useReservas = (filtros = {}) =>
  useQuery({
    queryKey: ['reservas', 'lista', filtros],
    queryFn: () => listarReservas(filtros),
    placeholderData: keepPreviousData,
  });

function useMutacion(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () =>
      Promise.all(AFECTADAS.map((queryKey) => queryClient.invalidateQueries({ queryKey }))),
  });
}

export const useCrearReserva = () => useMutacion(crearReserva);
export const useCancelarReserva = () => useMutacion(cancelarReserva);
export const useRetirarReserva = () => useMutacion(retirarReserva);
export const useVencerReservas = () => useMutacion(vencerReservas);
