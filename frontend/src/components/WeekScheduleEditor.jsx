import { useState } from 'react';
import { MAX_FRANJAS_POR_DIA } from '../features/sedes/horarios.js';
import { DIAS } from '../utils/formato.js';
import Button from './Button.jsx';
import estilos from './WeekScheduleEditor.module.css';

/**
 * Editor semanal de franjas: una fila por día con sus franjas (apertura y cierre), «Agregar
 * franja», «Quitar», «Cerrado» (sin franjas) y «Copiar a otros días». Marca los problemas mientras
 * se escribe (ver `validarHorarios`).
 *
 * @param {{valor: Record<number, {apertura: string, cierre: string}[]>, onCambiar: (nuevo: object) => void, problemas?: Record<number|string, string[]>}} props
 */
export default function WeekScheduleEditor({ valor, onCambiar, problemas = {} }) {
  const [copiando, setCopiando] = useState(null);
  const [destinos, setDestinos] = useState([]);

  const cambiarDia = (dia, franjas) => onCambiar({ ...valor, [dia]: franjas });
  const cambiarFranja = (dia, indice, campo, texto) =>
    cambiarDia(
      dia,
      valor[dia].map((f, i) => (i === indice ? { ...f, [campo]: texto } : f)),
    );
  const agregar = (dia) => {
    const ultima = valor[dia].at(-1);
    cambiarDia(dia, [
      ...valor[dia],
      ultima ? { apertura: ultima.cierre, cierre: '' } : { apertura: '09:00', cierre: '13:00' },
    ]);
  };

  function copiar() {
    const origen = valor[copiando].map((f) => ({ ...f }));
    const nuevo = { ...valor };
    for (const dia of destinos) nuevo[dia] = origen.map((f) => ({ ...f }));
    onCambiar(nuevo);
    setCopiando(null);
    setDestinos([]);
  }

  return (
    <div className={estilos.editor}>
      {problemas.general && (
        <p className={estilos.error} role="alert">
          {problemas.general.join(' ')}
        </p>
      )}
      {DIAS.map(({ numero, nombre }) => {
        const franjas = valor[numero] ?? [];
        const lista = problemas[numero] ?? [];
        return (
          <fieldset key={numero} className={estilos.dia}>
            <legend className={estilos.nombre}>{nombre}</legend>
            {franjas.length === 0 && <p className={estilos.cerrado}>Cerrado</p>}
            {franjas.map((franja, indice) => (
              <div key={indice} className={estilos.franja}>
                <label>
                  <span className={estilos.etiqueta}>
                    {`${nombre}, franja ${indice + 1}: apertura`}
                  </span>
                  <input
                    type="time"
                    value={franja.apertura}
                    onChange={(e) => cambiarFranja(numero, indice, 'apertura', e.target.value)}
                    aria-invalid={lista.length > 0 || undefined}
                  />
                </label>
                <label>
                  <span
                    className={estilos.etiqueta}
                  >{`${nombre}, franja ${indice + 1}: cierre`}</span>
                  <input
                    type="time"
                    value={franja.cierre}
                    onChange={(e) => cambiarFranja(numero, indice, 'cierre', e.target.value)}
                    aria-invalid={lista.length > 0 || undefined}
                  />
                </label>
                <Button
                  variante="link"
                  tamano="sm"
                  aria-label={`Quitar ${nombre}, franja ${indice + 1}`}
                  onClick={() =>
                    cambiarDia(
                      numero,
                      franjas.filter((_, i) => i !== indice),
                    )
                  }
                >
                  Quitar
                </Button>
              </div>
            ))}
            {lista.length > 0 && (
              <ul className={estilos.problemas} role="alert">
                {lista.map((texto) => (
                  <li key={texto}>{texto}</li>
                ))}
              </ul>
            )}
            <div className={estilos.acciones}>
              <Button
                variante="secondary"
                tamano="sm"
                disabled={franjas.length >= MAX_FRANJAS_POR_DIA}
                onClick={() => agregar(numero)}
                aria-label={`Agregar franja el ${nombre}`}
              >
                Agregar franja
              </Button>
              <Button
                variante="secondary"
                tamano="sm"
                disabled={franjas.length === 0}
                onClick={() => cambiarDia(numero, [])}
                aria-label={`Marcar ${nombre} como cerrado`}
              >
                Cerrado
              </Button>
              <Button
                variante="link"
                tamano="sm"
                disabled={franjas.length === 0}
                aria-expanded={copiando === numero}
                onClick={() => {
                  setCopiando(copiando === numero ? null : numero);
                  setDestinos([]);
                }}
                aria-label={`Copiar el horario del ${nombre} a otros días`}
              >
                Copiar a otros días
              </Button>
            </div>
            {copiando === numero && (
              <div className={estilos.copiar} role="group" aria-label={`Copiar ${nombre} a`}>
                {DIAS.filter((d) => d.numero !== numero).map((d) => (
                  <label key={d.numero} className={estilos.destino}>
                    <input
                      type="checkbox"
                      checked={destinos.includes(d.numero)}
                      onChange={(e) =>
                        setDestinos((actual) =>
                          e.target.checked
                            ? [...actual, d.numero]
                            : actual.filter((x) => x !== d.numero),
                        )
                      }
                    />
                    {d.nombre}
                  </label>
                ))}
                <Button tamano="sm" disabled={destinos.length === 0} onClick={copiar}>
                  Copiar
                </Button>
              </div>
            )}
          </fieldset>
        );
      })}
    </div>
  );
}
