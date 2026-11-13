import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  buscarPosiblesDuplicados,
  crearCuentaSocio,
  crearSocio,
  darDeBajaSocio,
  inhabilitarSocio,
  listarSocios,
  modificarSocio,
  obtenerSocio,
  reactivarSocio,
  rehabilitarSocio,
} from '../../../api/socios.js';

/** Claves de caché de socios: invalidar `claves.todos` refresca listado y fichas. */
export const claves = {
  todos: ['socios'],
  lista: (filtros) => ['socios', 'lista', filtros],
  detalle: (id) => ['socios', 'detalle', String(id)],
  duplicados: (criterio) => ['socios', 'duplicados', criterio],
};

export function useSocios(filtros = {}) {
  return useQuery({
    queryKey: claves.lista(filtros),
    queryFn: () => listarSocios(filtros),
    placeholderData: keepPreviousData,
  });
}

export function useSocio(id, opciones = {}) {
  return useQuery({ queryKey: claves.detalle(id), queryFn: () => obtenerSocio(id), ...opciones });
}

/** Búsqueda previa al alta: solo consulta cuando hay un criterio completo. */
export function usePosiblesDuplicados(criterio) {
  const porDocumento = Boolean(criterio.tipo_documento && criterio.nro_documento);
  const porPersona = Boolean(criterio.nombre && criterio.apellido && criterio.fecha_nacimiento);
  return useQuery({
    queryKey: claves.duplicados(criterio),
    queryFn: () => buscarPosiblesDuplicados(criterio),
    enabled: porDocumento || porPersona,
  });
}

/** Mutación que, termine bien o mal, deja el listado y la ficha con los datos vigentes. */
function useMutacionDeSocios(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: claves.todos }),
  });
}

export const useCrearSocio = () => useMutacionDeSocios(crearSocio);
export const useModificarSocio = (id) => useMutacionDeSocios((datos) => modificarSocio(id, datos));
export const useInhabilitarSocio = () =>
  useMutacionDeSocios(({ id, motivo }) => inhabilitarSocio(id, motivo));
export const useRehabilitarSocio = () => useMutacionDeSocios(rehabilitarSocio);
export const useBajaSocio = () =>
  useMutacionDeSocios(({ id, motivo }) => darDeBajaSocio(id, motivo));
export const useReactivarSocio = () => useMutacionDeSocios(reactivarSocio);
export const useCrearCuentaSocio = () =>
  useMutacionDeSocios(({ id, ...datos }) => crearCuentaSocio(id, datos));
