import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { ConPermiso } from '../auth/ConPermiso'
import { LoginPage } from '../auth/LoginPage'
import { SECCIONES } from '../auth/permisos'
import { RutaProtegida } from '../auth/RutaProtegida'
import { SinPermisoPage } from '../auth/SinPermisoPage'
import { AppShell } from '../components/AppShell/AppShell'
import { CatalogoPage } from '../features/catalogo/CatalogoPage'
import { DevolucionesPage } from '../features/devoluciones/DevolucionesPage'
import { DisponibilidadPage } from '../features/disponibilidad/DisponibilidadPage'
import { EnviosPage } from '../features/envios/EnviosPage'
import { PrestamosPage } from '../features/prestamos/PrestamosPage'
import { ReportesPage } from '../features/reportes/ReportesPage'
import { ReservasPage } from '../features/reservas/ReservasPage'
import { SedesPage } from '../features/sedes/SedesPage'
import { SociosPage } from '../features/socios/SociosPage'
import { TableroPage } from '../features/tablero/TableroPage'

// Pantalla de cada sección. Qué rol ve cada una se define en auth/permisos.ts.
const PANTALLAS: Record<string, ReactNode> = {
  '/': <TableroPage />,
  '/prestamos': <PrestamosPage />,
  '/envios': <EnviosPage />,
  '/reservas': <ReservasPage />,
  '/devoluciones': <DevolucionesPage />,
  '/disponibilidad': <DisponibilidadPage />,
  '/sedes': <SedesPage />,
  '/socios': <SociosPage />,
  '/catalogo': <CatalogoPage />,
  '/reportes': <ReportesPage />,
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Todo lo demás exige sesión. AppShell dibuja el menú; cada ruta se muestra en su <Outlet />.
          Una sección que el rol no puede ver lleva a /sin-permiso. */}
      <Route element={<RutaProtegida />}>
        <Route element={<AppShell />}>
          {SECCIONES.map((seccion) => (
            <Route
              key={seccion.ruta}
              path={seccion.ruta}
              element={<ConPermiso seccion={seccion}>{PANTALLAS[seccion.ruta]}</ConPermiso>}
            />
          ))}
          <Route path="/sin-permiso" element={<SinPermisoPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
