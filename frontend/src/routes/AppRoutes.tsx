import { Route, Routes } from 'react-router'
import { TableroPage } from '../features/tablero/TableroPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<TableroPage />} />
    </Routes>
  )
}
