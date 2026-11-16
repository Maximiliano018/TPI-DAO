import { forwardRef, useState } from 'react';
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

/** Ojo abierto (mostrar) o tachado (ocultar), de tinta como el resto de los íconos. */
function Ojo({ tachado }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <path
        d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
      {tachado && (
        <path d="M4 20 20 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      )}
    </svg>
  );
}

/**
 * Contraseña con un botón de ojo dentro del campo para mostrarla u ocultarla.
 * El botón anuncia su estado con `aria-pressed` y cambia su nombre accesible.
 */
export const InputClave = forwardRef(function InputClave(
  { etiqueta, ayuda, error, requerido, ...resto },
  ref,
) {
  const [visible, setVisible] = useState(false);
  return (
    <FormField etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      {(a11y) => (
        <div className={estilos.conBoton}>
          <input
            ref={ref}
            className={estilos.control}
            required={requerido}
            {...a11y}
            {...resto}
            type={visible ? 'text' : 'password'}
          />
          <button
            type="button"
            className={estilos.botonOjo}
            aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            aria-pressed={visible}
            onClick={() => setVisible((v) => !v)}
          >
            <Ojo tachado={visible} />
          </button>
        </div>
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
