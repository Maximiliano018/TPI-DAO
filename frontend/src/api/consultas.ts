// Una función por endpoint. TanStack Query guarda las consultas en caché por `queryKey`;
// después de cada cambio (mutación) se invalidan para que las pantallas se actualicen.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type {
  Categoria,
  NuevoLibro,
  DisponibilidadLibro,
  Devolucion,
  Ejemplar,
  EnviosExitosos,
  Libro,
  LibroSolicitado,
  MovimientoRemito,
  MovimientoSedes,
  Prestamo,
  Remito,
  Reserva,
  Sede,
  Socio,
  Tablero,
  VencidosMultas,
} from './tipos'

/** Arma "?a=1&b=2" ignorando los parámetros vacíos. */
function query(params: Record<string, string | number | boolean | null | undefined>) {
  const definidos = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return definidos.length ? `?${new URLSearchParams(definidos.map(([k, v]) => [k, String(v)]))}` : ''
}

function useConsulta<T>(ruta: string) {
  return useQuery({ queryKey: [ruta], queryFn: () => apiFetch<T>(ruta) })
}

export const useTablero = () => useConsulta<Tablero>('/tablero')
export const useSedes = () => useConsulta<Sede[]>('/sedes')
export const useSocios = (buscar: string) => useConsulta<Socio[]>(`/socios${query({ buscar })}`)
export const useLibros = (buscar: string) => useConsulta<Libro[]>(`/libros${query({ buscar })}`)
export const useEjemplares = (libroId: number) =>
  useConsulta<Ejemplar[]>(`/ejemplares${query({ libro_id: libroId })}`)
export const useDisponibilidad = (buscar: string) =>
  useConsulta<DisponibilidadLibro[]>(`/disponibilidad${query({ buscar })}`)
export const usePrestamos = (abiertos: boolean) =>
  useConsulta<Prestamo[]>(`/prestamos${query({ abiertos })}`)
export const useRemitos = (estado: string) =>
  useConsulta<Remito[]>(`/remitos${query({ estado })}`)
export const useMovimientosRemito = (remitoId: number) =>
  useConsulta<MovimientoRemito[]>(`/remitos/${remitoId}/movimientos`)
export const useReservas = (abiertas: boolean) =>
  useConsulta<Reserva[]>(`/reservas${query({ abiertas })}`)
export const useDevoluciones = () => useConsulta<Devolucion[]>('/devoluciones')

type Periodo = { desde: string; hasta: string }
export const useMovimientoSedes = (p: Periodo) =>
  useConsulta<MovimientoSedes>(`/reportes/movimiento-entre-sedes${query(p)}`)
export const useEnviosExitosos = (p: Periodo) =>
  useConsulta<EnviosExitosos>(`/reportes/envios-exitosos${query(p)}`)
export const useLibrosMasSolicitados = (p: Periodo) =>
  useConsulta<LibroSolicitado[]>(`/reportes/libros-mas-solicitados${query(p)}`)
export const useVencidosMultas = () => useConsulta<VencidosMultas>('/reportes/vencidos-y-multas')
export const useCategorias = () => useConsulta<Categoria[]>('/categorias')

// ------------------------------------------------------------------ Cambios

/** Ejecuta un cambio y, si sale bien, recarga todas las consultas (catálogo, disponibilidad...). */
function useCambio<D, R>(enviar: (datos: D) => Promise<R>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: enviar,
    onSuccess: () => queryClient.invalidateQueries(),
  })
}

export const useCrearLibro = () =>
  useCambio((libro: NuevoLibro) =>
    apiFetch<{ id: number }>('/libros', { method: 'POST', body: JSON.stringify(libro) }),
  )

export const useEliminarLibro = () =>
  useCambio((libroId: number) => apiFetch<void>(`/libros/${libroId}`, { method: 'DELETE' }))
