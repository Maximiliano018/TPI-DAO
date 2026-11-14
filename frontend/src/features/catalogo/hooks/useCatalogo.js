import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  buscarLibros,
  crearEjemplar,
  crearLibro,
  darDeBajaEjemplar,
  eliminarLibro,
  listarCategorias,
  listarEjemplares,
  modificarEjemplar,
  modificarLibro,
  obtenerDisponibilidad,
  obtenerEjemplar,
  obtenerLibro,
  recuperarEjemplar,
  repararEjemplar,
} from '../../../api/catalogo.js';

/** Claves de caché: invalidar `claves.todos` refresca libros, disponibilidad y ejemplares. */
export const claves = {
  todos: ['catalogo'],
  categorias: ['catalogo', 'categorias'],
  libros: (filtros) => ['catalogo', 'libros', filtros],
  libro: (id) => ['catalogo', 'libro', String(id)],
  disponibilidad: (id) => ['catalogo', 'disponibilidad', String(id)],
  ejemplares: (filtros) => ['catalogo', 'ejemplares', filtros],
  ejemplar: (id) => ['catalogo', 'ejemplar', String(id)],
};

export const useCategorias = () =>
  useQuery({ queryKey: claves.categorias, queryFn: listarCategorias, staleTime: Infinity });

export function useLibros(filtros = {}) {
  return useQuery({
    queryKey: claves.libros(filtros),
    queryFn: () => buscarLibros(filtros),
    placeholderData: keepPreviousData,
  });
}

export const useLibro = (id, opciones = {}) =>
  useQuery({ queryKey: claves.libro(id), queryFn: () => obtenerLibro(id), ...opciones });

export const useDisponibilidad = (id) =>
  useQuery({ queryKey: claves.disponibilidad(id), queryFn: () => obtenerDisponibilidad(id) });

export function useEjemplares(filtros = {}, opciones = {}) {
  return useQuery({
    queryKey: claves.ejemplares(filtros),
    queryFn: () => listarEjemplares(filtros),
    placeholderData: keepPreviousData,
    ...opciones,
  });
}

export const useEjemplar = (id) =>
  useQuery({ queryKey: claves.ejemplar(id), queryFn: () => obtenerEjemplar(id) });

/** Mutación que, termine bien o mal, deja todo el catálogo con los datos vigentes. */
function useMutacionDelCatalogo(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: claves.todos }),
  });
}

export const useCrearLibro = () => useMutacionDelCatalogo(crearLibro);
export const useModificarLibro = (id) =>
  useMutacionDelCatalogo((datos) => modificarLibro(id, datos));
export const useEliminarLibro = () => useMutacionDelCatalogo(eliminarLibro);
export const useCrearEjemplar = () => useMutacionDelCatalogo(crearEjemplar);
export const useModificarEjemplar = () =>
  useMutacionDelCatalogo(({ id, ...datos }) => modificarEjemplar(id, datos));
export const useBajaEjemplar = () =>
  useMutacionDelCatalogo(({ id, ...datos }) => darDeBajaEjemplar(id, datos));
export const useRepararEjemplar = () =>
  useMutacionDelCatalogo(({ id, version }) => repararEjemplar(id, version));
export const useRecuperarEjemplar = () =>
  useMutacionDelCatalogo(({ id, ...datos }) => recuperarEjemplar(id, datos));
