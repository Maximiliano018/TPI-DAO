import { useId, useMemo, useState } from 'react';
import { normalizar } from '../utils/texto.js';
import estilos from './Combobox.module.css';

/**
 * Lista desplegable con búsqueda (patrón combobox ARIA 1.2): el foco queda en el campo y la
 * opción activa se indica con `aria-activedescendant`. Flechas navegan, Enter elige, Escape cierra.
 *
 * @param {{etiqueta: string, opciones: {id: number|string, texto: string, detalle?: string}[], valor: number|string|'', onCambiar: (id: number|string|'') => void, error?: string, ayuda?: string, requerido?: boolean}} props
 */
export default function Combobox({
  etiqueta,
  opciones,
  valor,
  onCambiar,
  error,
  ayuda,
  requerido = false,
  placeholder = 'Escriba para buscar',
  inputRef,
  ...resto
}) {
  const id = useId();
  const seleccionada = opciones.find((o) => o.id === valor);
  const [consulta, setConsulta] = useState(null); // null: se muestra la opción elegida
  const [abierto, setAbierto] = useState(false);
  const [activa, setActiva] = useState(0);

  const texto = consulta ?? seleccionada?.texto ?? '';
  const filtradas = useMemo(() => {
    const q = normalizar(consulta ?? '');
    return q ? opciones.filter((o) => normalizar(o.texto).includes(q)) : opciones;
  }, [opciones, consulta]);

  const idOpcion = (indice) => `${id}-op-${indice}`;
  const idAyuda = ayuda ? `${id}-ayuda` : undefined;
  const idError = error ? `${id}-error` : undefined;

  function elegir(opcion) {
    onCambiar(opcion.id);
    setConsulta(null);
    setAbierto(false);
  }

  function alPresionar(evento) {
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      setAbierto(true);
      setActiva((i) => Math.min(i + 1, filtradas.length - 1));
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      setActiva((i) => Math.max(i - 1, 0));
    } else if (evento.key === 'Enter' && abierto && filtradas[activa]) {
      evento.preventDefault();
      elegir(filtradas[activa]);
    } else if (evento.key === 'Escape' && abierto) {
      evento.stopPropagation();
      setAbierto(false);
      setConsulta(null);
    }
  }

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
      <input
        ref={inputRef}
        id={id}
        role="combobox"
        aria-expanded={abierto}
        aria-controls={`${id}-lista`}
        aria-autocomplete="list"
        aria-activedescendant={abierto && filtradas[activa] ? idOpcion(activa) : undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={[idAyuda, idError].filter(Boolean).join(' ') || undefined}
        autoComplete="off"
        className={estilos.control}
        placeholder={placeholder}
        value={texto}
        onChange={(e) => {
          setConsulta(e.target.value);
          setAbierto(true);
          setActiva(0);
          if (e.target.value === '' && valor !== '') onCambiar('');
        }}
        onFocus={() => setAbierto(true)}
        onBlur={() => {
          setAbierto(false);
          setConsulta(null);
        }}
        onKeyDown={alPresionar}
        {...resto}
      />
      <ul
        id={`${id}-lista`}
        role="listbox"
        aria-label={etiqueta}
        className={estilos.lista}
        hidden={!abierto}
      >
        {filtradas.length === 0 && (
          <li role="presentation" className={estilos.vacio}>
            Sin coincidencias
          </li>
        )}
        {filtradas.map((opcion, indice) => (
          <li
            key={opcion.id}
            id={idOpcion(indice)}
            role="option"
            aria-selected={opcion.id === valor}
            className={`${estilos.opcion} ${indice === activa ? estilos.activa : ''}`}
            // mousedown (y no click) para que el campo no pierda el foco antes de elegir
            onMouseDown={(e) => {
              e.preventDefault();
              elegir(opcion);
            }}
          >
            {opcion.texto}
            {opcion.detalle && <span className={estilos.detalle}> · {opcion.detalle}</span>}
          </li>
        ))}
      </ul>
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
