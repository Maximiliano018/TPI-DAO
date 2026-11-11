import { useEffect } from 'react';

const FOCALIZABLES =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Mantiene el foco dentro de `ref` mientras `activo`; Escape llama a `onEscape`.
 * Devuelve el foco al elemento que lo tenía antes de activarse.
 */
export function useAtraparFoco(ref, activo, onEscape) {
  useEffect(() => {
    if (!activo || !ref.current) return undefined;
    const previo = document.activeElement;
    const elementos = () => [...ref.current.querySelectorAll(FOCALIZABLES)];
    elementos()[0]?.focus();

    function alPresionar(evento) {
      if (evento.key === 'Escape') {
        onEscape?.();
        return;
      }
      if (evento.key !== 'Tab') return;
      const lista = elementos();
      if (lista.length === 0) return;
      if (evento.shiftKey && document.activeElement === lista[0]) {
        evento.preventDefault();
        lista[lista.length - 1].focus();
      } else if (!evento.shiftKey && document.activeElement === lista[lista.length - 1]) {
        evento.preventDefault();
        lista[0].focus();
      }
    }
    document.addEventListener('keydown', alPresionar);
    return () => {
      document.removeEventListener('keydown', alPresionar);
      if (previo instanceof HTMLElement) previo.focus();
    };
  }, [ref, activo, onEscape]);
}
