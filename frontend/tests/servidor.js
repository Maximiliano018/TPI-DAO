import { setupServer } from 'msw/node';

/** Servidor MSW compartido: cada prueba agrega sus handlers con `servidor.use(...)`. */
export const servidor = setupServer();
