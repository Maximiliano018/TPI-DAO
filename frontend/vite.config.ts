import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Las llamadas a /api se reenvían al backend FastAPI: así el front no tiene problemas de CORS.
    // 127.0.0.1 y no "localhost": Node puede resolver localhost a IPv6 (::1) y uvicorn escucha en IPv4.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
