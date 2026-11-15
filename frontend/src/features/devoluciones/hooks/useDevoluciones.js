import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  iniciarPago,
  listarMultas,
  obtenerPago,
  registrarDevolucion,
  saldarMulta,
  pagarEnLinea,
} from '../../../api/devoluciones.js';

// La devolución toca el préstamo, el ejemplar, los remitos, las reservas y al socio.
const AFECTADAS = [['prestamos'], ['remitos'], ['catalogo'], ['socios'], ['reservas'], ['multas']];

function useMutacion(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () =>
      Promise.all(AFECTADAS.map((queryKey) => queryClient.invalidateQueries({ queryKey }))),
  });
}

export const useMultas = (filtros = {}) =>
  useQuery({
    queryKey: ['multas', 'lista', filtros],
    queryFn: () => listarMultas(filtros),
    placeholderData: keepPreviousData,
  });

export const useRegistrarDevolucion = () =>
  useMutacion(({ id, ...datos }) => registrarDevolucion(id, datos));
export const useSaldarMulta = () => useMutacion(saldarMulta);
export const useIniciarPago = () => useMutacion(iniciarPago);
export const usePagarEnLinea = () => useMutacion(pagarEnLinea);
export const usePago = (id) =>
  useQuery({ queryKey: ['multas', 'pago', String(id)], queryFn: () => obtenerPago(id) });
