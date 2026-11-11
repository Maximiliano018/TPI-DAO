import { useId } from 'react';
import estilos from './FormField.module.css';

/**
 * Etiqueta, ayuda y error asociados al control por `aria-describedby`.
 * `children` recibe las props de accesibilidad que debe aplicar al control.
 */
export default function FormField({ etiqueta, ayuda, error, requerido = false, children }) {
  const id = useId();
  const idAyuda = ayuda ? `${id}-ayuda` : undefined;
  const idError = error ? `${id}-error` : undefined;
  const describedBy = [idAyuda, idError].filter(Boolean).join(' ') || undefined;
  return (
    <div className={estilos.campo}>
      <label htmlFor={id} className={estilos.etiqueta}>
        {etiqueta}
        {requerido && (
          <span aria-hidden="true" className={estilos.requerido}>
            {' *'}
          </span>
        )}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {ayuda && (
        <p id={idAyuda} className={estilos.ayuda}>
          {ayuda}
        </p>
      )}
      {error && (
        <p id={idError} className={estilos.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
