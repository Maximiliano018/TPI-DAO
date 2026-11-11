import { forwardRef } from 'react';
import FormField from './FormField.jsx';
import estilos from './controles.module.css';

/** Campo de texto con etiqueta, ayuda y error. */
export const Input = forwardRef(function Input(
  { etiqueta, ayuda, error, requerido, ...resto },
  ref,
) {
  return (
    <FormField etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      {(a11y) => (
        <input ref={ref} className={estilos.control} required={requerido} {...a11y} {...resto} />
      )}
    </FormField>
  );
});

/** Lista desplegable nativa con etiqueta, ayuda y error. */
export const Select = forwardRef(function Select(
  { etiqueta, ayuda, error, requerido, children, ...resto },
  ref,
) {
  return (
    <FormField etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      {(a11y) => (
        <select ref={ref} className={estilos.control} {...a11y} {...resto}>
          {children}
        </select>
      )}
    </FormField>
  );
});

/** Área de texto con etiqueta, ayuda y error. */
export const Textarea = forwardRef(function Textarea(
  { etiqueta, ayuda, error, requerido, ...resto },
  ref,
) {
  return (
    <FormField etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      {(a11y) => <textarea ref={ref} className={estilos.control} {...a11y} {...resto} />}
    </FormField>
  );
});

/** Casilla de verificación con su etiqueta. */
export const Checkbox = forwardRef(function Checkbox({ etiqueta, ...resto }, ref) {
  return (
    <label className={estilos.casilla}>
      <input ref={ref} type="checkbox" {...resto} />
      {etiqueta}
    </label>
  );
});
