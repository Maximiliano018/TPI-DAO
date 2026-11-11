import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  historialSede,
  listarExcepciones,
  listarLocalidades,
  listarSedes,
  obtenerSede,
  resumenSedes,
} from '../../../api/sedes.js';

/** Claves de caché de sedes: invalidar `claves.todas` refresca listado, detalle y resumen. */
export const claves = {
  todas: ['sedes'],
  lista: (filtros) => ['sedes', 'lista', filtros],
  detalle: (id) => ['sedes', 'detalle', String(id)],
  resumen: ['sedes', 'resumen'],
  excepciones: (id, params) => ['sedes', 'excepciones', String(id), params ?? {}],
  historial: (id, filtros) => ['sedes', 'historial', String(id), filtros],
  localidades: ['localidades'],
};

/** Listado paginado de sedes (conserva la página anterior mientras llega la nueva). */
export function useSedes(filtros = {}, opciones = {}) {
  return useQuery({
    queryKey: claves.lista(filtros),
    queryFn: () => listarSedes(filtros),
    placeholderData: keepPreviousData,
    ...opciones,
  });
}

export function useSede(id, opciones = {}) {
  return useQuery({ queryKey: claves.detalle(id), queryFn: () => obtenerSede(id), ...opciones });
}

export function useResumenSedes(opciones = {}) {
  return useQuery({ queryKey: claves.resumen, queryFn: resumenSedes, ...opciones });
}

export function useExcepciones(id, params, opciones = {}) {
  return useQuery({
    queryKey: claves.excepciones(id, params),
    queryFn: () => listarExcepciones(id, params),
    ...opciones,
  });
}

export function useHistorialSede(id, filtros, opciones = {}) {
  return useQuery({
    queryKey: claves.historial(id, filtros),
    queryFn: () => historialSede(id, filtros),
    placeholderData: keepPreviousData,
    ...opciones,
  });
}

/** Catálogo cerrado de localidades; casi no cambia, se cachea toda la sesión. */
export function useLocalidades(opciones = {}) {
  return useQuery({
    queryKey: claves.localidades,
    queryFn: () => listarLocalidades(),
    staleTime: Infinity,
    gcTime: Infinity,
    ...opciones,
  });
}
