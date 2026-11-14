import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  aprobarSolicitud,
  buscarPosiblesDuplicados,
  crearCuentaSocio,
  crearSocio,
  darDeBajaSocio,
  historialSocio,
  inhabilitarSocio,
  listarSocios,
  modificarSocio,
  obtenerSocio,
  reactivarSocio,
  rechazarSolicitud,
  rehabilitarSocio,
  solicitarReactivacion,
} from '../../../api/socios.js';

/** Claves de caché de socios: invalidar `claves.todos` refresca listado y fichas. */
export const claves = {
  todos: ['socios'],
  lista: (filtros) => ['socios', 'lista', filtros],
  detalle: (id) => ['socios', 'detalle', String(id)],
  duplicados: (criterio) => ['socios', 'duplicados', criterio],
  historial: (id, filtros) => ['socios', 'historial', String(id), filtros],
};

export function useSocios(filtros = {}, opciones = {}) {
  return useQuery({
    queryKey: claves.lista(filtros),
    queryFn: () => listarSocios(filtros),
    placeholderData: keepPreviousData,
    ...opciones,
  });
}

/** Historial del socio (el socio ve el propio, sin la identidad del personal). */
export function useHistorialSocio(id, filtros, opciones = {}) {
  return useQuery({
    queryKey: claves.historial(id, filtros),
    queryFn: () => historialSocio(id, filtros),
    placeholderData: keepPreviousData,
    ...opciones,
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
  useMutacionDeSocios(({ id, tipo, motivo }) => darDeBajaSocio(id, tipo, motivo));
export const useReactivarSocio = () => useMutacionDeSocios(reactivarSocio);
export const useCrearCuentaSocio = () =>
  useMutacionDeSocios(({ id, ...datos }) => crearCuentaSocio(id, datos));
export const useSolicitarReactivacion = () =>
  useMutacionDeSocios(({ id, mensaje }) => solicitarReactivacion(id, mensaje));
export const useAprobarSolicitud = () => useMutacionDeSocios(aprobarSolicitud);
export const useRechazarSolicitud = () =>
  useMutacionDeSocios(({ id, motivo }) => rechazarSolicitud(id, motivo));
