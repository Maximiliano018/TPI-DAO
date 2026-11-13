import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { listarMultas, registrarDevolucion, saldarMulta } from '../../../api/devoluciones.js';

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
