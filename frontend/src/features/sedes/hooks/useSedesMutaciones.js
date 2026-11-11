import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  agregarExcepcion,
  crearSede,
  darDeBajaSede,
  modificarSede,
  quitarExcepcion,
  reactivarSede,
} from '../../../api/sedes.js';
import { claves } from './useSedes.js';

/**
 * Mutación que, termine bien o mal, refresca listado, detalle y resumen: ante un conflicto
 * («la sede ya estaba en ese estado») la pantalla queda con los datos vigentes.
 */
function useMutacionDeSedes(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: claves.todas }),
  });
}

export const useCrearSede = () => useMutacionDeSedes(crearSede);
export const useModificarSede = (id) => useMutacionDeSedes((datos) => modificarSede(id, datos));
export const useBajaSede = (id) => useMutacionDeSedes((datos) => darDeBajaSede(id, datos));
export const useReactivarSede = (id) => useMutacionDeSedes((datos) => reactivarSede(id, datos));
export const useAgregarExcepciones = (id) =>
  useMutacionDeSedes((datos) => agregarExcepcion(id, datos));
export const useQuitarExcepcion = (id) =>
  useMutacionDeSedes((excepcionId) => quitarExcepcion(id, excepcionId));
