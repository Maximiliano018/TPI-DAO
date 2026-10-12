// Formatos para mostrar datos de la API en español de Argentina.

/** "2026-10-12" → "12/10/2026". Se arma a mano para que no la corra la zona horaria. */
export function fecha(valor: string | null): string {
  if (!valor) return '—'
  const [anio, mes, dia] = valor.slice(0, 10).split('-')
  return `${dia}/${mes}/${anio}`
}

/** Instante ISO (UTC) → fecha y hora locales: "12/10/2026 14:30". */
export function fechaHora(valor: string | null): string {
  if (!valor) return '—'
  return new Date(valor).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Los importes viajan en centavos (enteros). Sin decimales si son pesos redondos. */
export function pesos(centavos: number | null): string {
  if (centavos === null) return '—'
  const decimales = centavos % 100 === 0 ? 0 : 2
  return (centavos / 100).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })
}

/** Número con coma decimal: 1.5 → "1,5". */
export function numero(valor: number | null): string {
  return valor === null ? '—' : valor.toLocaleString('es-AR')
}

/** "1 extraviado", "2 extraviados". */
export function plural(cantidad: number, singular: string, plural = `${singular}s`): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`
}

export function dias(cantidad: number): string {
  return `${cantidad} ${Math.abs(cantidad) === 1 ? 'día' : 'días'}`
}

const DIAS_SEMANA = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

export function diaSemana(numero: number): string {
  return DIAS_SEMANA[numero] ?? String(numero)
}

/** "08:00:00" → "08:00". */
export function hora(valor: string): string {
  return valor.slice(0, 5)
}
