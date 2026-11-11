import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  crearUsuario,
  darDeBajaUsuario,
  listarUsuarios,
  modificarUsuario,
  obtenerUsuario,
  reactivarUsuario,
} from '../../../api/usuarios.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';

/** Claves de caché de usuarios: invalidar `claves.todos` refresca listado y detalle. */
export const claves = {
  todos: ['usuarios'],
  lista: (filtros) => ['usuarios', 'lista', filtros],
  detalle: (id) => ['usuarios', 'detalle', String(id)],
};

export function useUsuarios(filtros = {}) {
  return useQuery({
    queryKey: claves.lista(filtros),
    queryFn: () => listarUsuarios(filtros),
    placeholderData: keepPreviousData,
  });
}

export function useUsuario(id, opciones = {}) {
  return useQuery({ queryKey: claves.detalle(id), queryFn: () => obtenerUsuario(id), ...opciones });
}

/** Mutación que, termine bien o mal, deja el listado y el detalle con los datos vigentes. */
function useMutacionDeUsuarios(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: claves.todos }),
  });
}

export const useCrearUsuario = () => useMutacionDeUsuarios(crearUsuario);
export const useModificarUsuario = (id) =>
  useMutacionDeUsuarios((datos) => modificarUsuario(id, datos));
export const useBajaUsuario = () => useMutacionDeUsuarios(darDeBajaUsuario);
export const useReactivarUsuario = () => useMutacionDeUsuarios(reactivarUsuario);

/** Sedes entre las que se puede asignar (solo activas) o filtrar (todas), de la más corta lista. */
export function useSedesParaElegir({ soloActivas }) {
  return useSedes({ estado: soloActivas ? 'ACTIVA' : 'TODAS', orden: 'nombre', size: 100 });
}
