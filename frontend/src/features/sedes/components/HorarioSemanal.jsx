import { DIAS, diaSemanaISO, textoHorarioDelDia } from '../../../utils/formato.js';
import estilos from './Sedes.module.css';

/** Semana de lunes a domingo con las franjas de cada día; resalta hoy. */
export default function HorarioSemanal({ horarios }) {
  const hoy = diaSemanaISO();
  return (
    <ul className={estilos.semana} aria-label="Horario semanal">
      {DIAS.map(({ numero, nombre }) => (
        <li
          key={numero}
          className={`${estilos.dia} ${numero === hoy ? estilos.hoy : ''}`}
          aria-current={numero === hoy ? 'date' : undefined}
        >
          <span>
            {nombre}
            {numero === hoy && ' (hoy)'}
          </span>
          <span>{textoHorarioDelDia(horarios, numero)}</span>
        </li>
      ))}
    </ul>
  );
}
