import { useId } from 'react';
import estilos from './Card.module.css';

/** Contenedor con superficie, borde y espaciado. Con `titulo` agrega un encabezado y se nombra. */
export default function Card({ titulo, acciones, as: Etiqueta = 'section', children, ...resto }) {
  const idTitulo = useId();
  return (
    <Etiqueta
      className={estilos.tarjeta}
      aria-labelledby={titulo ? idTitulo : undefined}
      {...resto}
    >
      {(titulo || acciones) && (
        <header className={estilos.encabezado}>
          {titulo && (
            <h2 id={idTitulo} className={estilos.titulo}>
              {titulo}
            </h2>
          )}
          {acciones}
        </header>
      )}
      {children}
    </Etiqueta>
  );
}
