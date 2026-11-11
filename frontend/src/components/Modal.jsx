import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import estilos from './Modal.module.css';

const FOCALIZABLES =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Diálogo modal accesible: atrapa el foco, Escape lo cierra (salvo `bloqueado`, mientras se
 * procesa) y devuelve el foco a quien lo abrió.
 *
 * @param {{titulo: string, onCerrar: () => void, bloqueado?: boolean, acciones?: import('react').ReactNode}} props
 */
export default function Modal({ titulo, onCerrar, bloqueado = false, acciones, children }) {
  const idTitulo = useId();
  const caja = useRef(null);
  const alCerrar = useRef(onCerrar);
  alCerrar.current = onCerrar;
  const estaBloqueado = useRef(bloqueado);
  estaBloqueado.current = bloqueado;

  useEffect(() => {
    const previo = document.activeElement;
    const elementos = () => [...caja.current.querySelectorAll(FOCALIZABLES)];
    const primero =
      caja.current.querySelector('[data-autofocus]') ?? elementos()[0] ?? caja.current;
    primero.focus();

    function alPresionar(evento) {
      if (evento.key === 'Escape' && !estaBloqueado.current) {
        evento.stopPropagation();
        alCerrar.current();
        return;
      }
      if (evento.key !== 'Tab') return;
      const lista = elementos();
      if (lista.length === 0) {
        evento.preventDefault();
        return;
      }
      const inicio = lista[0];
      const fin = lista[lista.length - 1];
      if (evento.shiftKey && document.activeElement === inicio) {
        evento.preventDefault();
        fin.focus();
      } else if (!evento.shiftKey && document.activeElement === fin) {
        evento.preventDefault();
        inicio.focus();
      }
    }
    document.addEventListener('keydown', alPresionar);
    return () => {
      document.removeEventListener('keydown', alPresionar);
      if (previo instanceof HTMLElement) previo.focus();
    };
  }, []);

  return createPortal(
    <div className={estilos.fondo}>
      <div
        ref={caja}
        className={estilos.caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
      >
        <h2 id={idTitulo} className={estilos.titulo}>
          {titulo}
        </h2>
        <div className={estilos.cuerpo}>{children}</div>
        {acciones && <div className={estilos.acciones}>{acciones}</div>}
      </div>
    </div>,
    document.body,
  );
}
