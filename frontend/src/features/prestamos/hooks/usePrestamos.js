import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  actualizarParametro,
  cancelarPrestamo,
  detectarVencidos,
  entregarPrestamo,
  listarParametros,
  listarPrestamos,
  obtenerPrestamo,
  registrarPrestamo,
  renovarPrestamo,
} from '../../../api/prestamos.js';
import {
  anularRemito,
  avanzarRemito,
  generarRemito,
  listarRemitos,
  marcarExtraviado,
  obtenerRemito,
  recibirRemito,
} from '../../../api/remitos.js';

// Préstamos, remitos y ejemplares cambian juntos: toda mutación refresca las tres cachés.
const AFECTADAS = [['prestamos'], ['remitos'], ['catalogo'], ['socios']];

export const claves = {
  prestamos: (filtros) => ['prestamos', 'lista', filtros],
  prestamo: (id) => ['prestamos', 'detalle', String(id)],
  remitos: (filtros) => ['remitos', 'lista', filtros],
  remito: (id) => ['remitos', 'detalle', String(id)],
  parametros: ['parametros'],
};

export const usePrestamos = (filtros = {}, opciones = {}) =>
  useQuery({
    queryKey: claves.prestamos(filtros),
    queryFn: () => listarPrestamos(filtros),
    placeholderData: keepPreviousData,
    ...opciones,
  });

export const usePrestamo = (id) =>
  useQuery({ queryKey: claves.prestamo(id), queryFn: () => obtenerPrestamo(id) });

export const useRemitos = (filtros = {}) =>
  useQuery({
    queryKey: claves.remitos(filtros),
    queryFn: () => listarRemitos(filtros),
    placeholderData: keepPreviousData,
  });

export const useRemito = (id) =>
  useQuery({ queryKey: claves.remito(id), queryFn: () => obtenerRemito(id) });

export const useParametros = () =>
  useQuery({ queryKey: claves.parametros, queryFn: listarParametros });

function useMutacion(mutationFn, extra = []) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () =>
      Promise.all(
        [...AFECTADAS, ...extra].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      ),
  });
}

export const useRegistrarPrestamo = () => useMutacion(registrarPrestamo);
export const useEntregarPrestamo = () => useMutacion(entregarPrestamo);
export const useRenovarPrestamo = () => useMutacion(renovarPrestamo);
export const useCancelarPrestamo = () =>
  useMutacion(({ id, motivo }) => cancelarPrestamo(id, motivo));
export const useDetectarVencidos = () => useMutacion(detectarVencidos);
export const useGenerarRemito = () => useMutacion(generarRemito);
export const useAvanzarRemito = () => useMutacion(({ id, accion }) => avanzarRemito(id, accion));
export const useRecibirRemito = () => useMutacion(({ id, lineas }) => recibirRemito(id, lineas));
export const useAnularRemito = () => useMutacion(({ id, motivo }) => anularRemito(id, motivo));
export const useMarcarExtraviado = () =>
  useMutacion(({ id, motivo }) => marcarExtraviado(id, motivo));
export const useActualizarParametro = () =>
  useMutacion(({ clave, valor }) => actualizarParametro(clave, valor), [claves.parametros]);
