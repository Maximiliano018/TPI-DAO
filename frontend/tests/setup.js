import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';
import { afterAll, afterEach, beforeAll, expect } from 'vitest';
import { guardarToken } from '../src/api/client.js';
import { servidor } from './servidor.js';

expect.extend(toHaveNoViolations);

// La primera pantalla que se carga con React.lazy tarda más en transformarse en frío.
configure({ asyncUtilTimeout: 4000 });

beforeAll(() => servidor.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup();
  servidor.resetHandlers();
  guardarToken(null);
  sessionStorage.clear();
});
afterAll(() => servidor.close());
