import { Route, Routes } from 'react-router'
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

export function AppRoutes() {
  return (
    <Routes>
      {/* AppShell dibuja el menú y la barra; cada ruta hija se muestra en su <Outlet /> */}
      <Route element={<AppShell />}>
        <Route path="/" element={<TableroPage />} />
        <Route path="/prestamos" element={<PrestamosPage />} />
        <Route path="/envios" element={<EnviosPage />} />
        <Route path="/reservas" element={<ReservasPage />} />
        <Route path="/devoluciones" element={<DevolucionesPage />} />
        <Route path="/disponibilidad" element={<DisponibilidadPage />} />
        <Route path="/sedes" element={<SedesPage />} />
        <Route path="/socios" element={<SociosPage />} />
        <Route path="/catalogo" element={<CatalogoPage />} />
        <Route path="/reportes" element={<ReportesPage />} />
      </Route>
    </Routes>
  )
}
