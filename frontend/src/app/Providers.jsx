import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { SesionProvider } from '../auth/SesionContext.jsx';
import { ToastProvider } from '../components/index.js';

/** Un error 4xx no se reintenta (es una respuesta definitiva del servidor); los de red, una vez. */
export function crearQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (intentos, error) => !(error?.estado >= 400 && error?.estado < 500) && intentos < 1,
      },
    },
  });
}

/** Caché de datos del servidor, sesión y notificaciones. */
export default function Providers({ children, queryClient }) {
  const [cliente] = useState(() => queryClient ?? crearQueryClient());
  return (
    <QueryClientProvider client={cliente}>
      <SesionProvider>
        <ToastProvider>{children}</ToastProvider>
      </SesionProvider>
    </QueryClientProvider>
  );
}
