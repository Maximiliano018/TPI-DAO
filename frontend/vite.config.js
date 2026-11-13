import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';

const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8'));

// La API del backend se consume en /api; en desarrollo se redirige al puerto 8000.
// Se usa 127.0.0.1 y no `localhost`: en Windows Node resuelve `localhost` a ::1 (IPv6) y uvicorn
// escucha solo en IPv4, así que el proxy respondía 500.
export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(version) },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    // Origen de las URL relativas: MSW las resuelve contra `location` (handlers en http://localhost).
    environmentOptions: { jsdom: { url: 'http://localhost/' } },
    globals: true,
    // Las pruebas de formularios tipean campo por campo y corren axe: con la suite en paralelo
    // y las pantallas cargándose en frío (React.lazy) pueden pasar los 5 s por defecto.
    testTimeout: 15000,
    setupFiles: ['./tests/setup.js'],
    include: ['src/**/*.test.{js,jsx}', 'tests/**/*.test.{js,jsx}'],
  },
});
