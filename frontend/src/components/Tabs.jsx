import { useId, useRef } from 'react';
import estilos from './Tabs.module.css';

/**
 * Pestañas accesibles (patrón WAI-ARIA): flechas, Inicio y Fin mueven la selección.
 *
 * @param {{tabs: {id: string, titulo: string, contenido: import('react').ReactNode}[], activa: string, onCambiar: (id: string) => void}} props
 */
export default function Tabs({ tabs, activa, onCambiar }) {
  const base = useId();
  const refs = useRef({});

  function alPresionar(evento, indice) {
    const mover = { ArrowRight: 1, ArrowLeft: -1 }[evento.key];
    let destino = null;
    if (mover) destino = (indice + mover + tabs.length) % tabs.length;
    if (evento.key === 'Home') destino = 0;
    if (evento.key === 'End') destino = tabs.length - 1;
    if (destino === null) return;
    evento.preventDefault();
    onCambiar(tabs[destino].id);
    refs.current[tabs[destino].id]?.focus();
  }

  return (
    <div>
      <div role="tablist" className={estilos.lista}>
        {tabs.map((tab, indice) => (
          <button
            key={tab.id}
            ref={(el) => (refs.current[tab.id] = el)}
            role="tab"
            type="button"
            id={`${base}-tab-${tab.id}`}
            aria-selected={tab.id === activa}
            aria-controls={`${base}-panel-${tab.id}`}
            tabIndex={tab.id === activa ? 0 : -1}
            className={`${estilos.tab} ${tab.id === activa ? estilos.activa : ''}`}
            onClick={() => onCambiar(tab.id)}
            onKeyDown={(e) => alPresionar(e, indice)}
          >
            {tab.titulo}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${base}-panel-${tab.id}`}
          aria-labelledby={`${base}-tab-${tab.id}`}
          hidden={tab.id !== activa}
          className={estilos.panel}
        >
          {tab.id === activa && tab.contenido}
        </div>
      ))}
    </div>
  );
}
