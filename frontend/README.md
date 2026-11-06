# frontend

Aplicación React 18 con JavaScript y Vite. Detalle en [docs/tecnica/09-frontend.md](../docs/tecnica/09-frontend.md).

## Estructura

`src/` se organiza por funcionalidad: `app` (providers, rutas, layout), `api` (cliente HTTP), `auth` (sesión y rutas protegidas), `components` (design system), `features/<proceso>/{pages,components,hooks}`, `hooks`, `utils` y `styles`. Las pruebas viven junto al código (`*.test.jsx`) y las utilidades compartidas en `tests/`.

## Comandos

Requiere Node 20 o superior (ver `.nvmrc`).

```bash
npm install
npm run dev           # http://localhost:5173 (el proxy /api apunta al backend en :8000)
npm run lint
npm run format:check
npm test
npm run build
```
