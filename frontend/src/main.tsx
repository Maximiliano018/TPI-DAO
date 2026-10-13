import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { ApiError } from './api/client.ts'
import { ProveedorSesion } from './auth/ProveedorSesion.tsx'
import { AppRoutes } from './routes/AppRoutes.tsx'
import './styles/tokens.css'
import './styles/base.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Un 4xx (sin sesión, sin permiso, no encontrado) no se arregla reintentando.
      retry: (intentos, error) =>
        !(error instanceof ApiError && error.status < 500) && intentos < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ProveedorSesion>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ProveedorSesion>
    </QueryClientProvider>
  </StrictMode>,
)
