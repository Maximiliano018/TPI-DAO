import { useEffect } from 'react';
import { MENSAJES } from '../utils/mensajes.js';

/** Título del documento y foco en el encabezado al cambiar de pantalla (lectores de pantalla). */
export function useTituloDePagina(titulo) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · ${MENSAJES.sistema}` : MENSAJES.sistema;
  }, [titulo]);
}
