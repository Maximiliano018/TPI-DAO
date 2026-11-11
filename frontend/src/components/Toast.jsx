import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import estilos from './Toast.module.css';

const ToastContext = createContext(null);
const DURACION_MS = 6000;

/** Proveedor de notificaciones. Se anuncian con `aria-live` y desaparecen solas. */
export function ToastProvider({ children }) {
  const [avisos, setAvisos] = useState([]);

  const descartar = useCallback((id) => setAvisos((lista) => lista.filter((a) => a.id !== id)), []);
  const mostrar = useCallback(
    (texto, tono = 'success') => {
      const id = `${Date.now()}-${Math.random()}`;
      setAvisos((lista) => [...lista, { id, texto, tono }]);
      setTimeout(() => descartar(id), DURACION_MS);
    },
    [descartar],
  );
  const valor = useMemo(() => ({ mostrar }), [mostrar]);

  return (
    <ToastContext.Provider value={valor}>
      {children}
      <div className={estilos.region} aria-live="polite" aria-atomic="false">
        {avisos.map((aviso) => (
          <div key={aviso.id} className={`${estilos.aviso} ${estilos[aviso.tono]}`} role="status">
            <span>{aviso.texto}</span>
            <button
              type="button"
              className={estilos.cerrar}
              aria-label="Cerrar aviso"
              onClick={() => descartar(aviso.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** `const { mostrar } = useToast(); mostrar('Sede guardada')` */
export function useToast() {
  const contexto = useContext(ToastContext);
  if (!contexto) throw new Error('useToast debe usarse dentro de ToastProvider');
  return contexto;
}
