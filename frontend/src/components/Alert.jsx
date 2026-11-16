import Icono from './Icono.jsx';
import estilos from './Alert.module.css';

const ICONOS = { success: 'ok', warning: 'alerta', danger: 'error', info: 'info' };

/**
 * Aviso en línea. Los errores usan `role="alert"`; el resto, `role="status"`.
 *
 * @param {{tono?: 'success'|'warning'|'danger'|'info', titulo?: string}} props
 */
export default function Alert({ tono = 'info', titulo, children, ...resto }) {
  return (
    <div
      className={`${estilos.alerta} ${estilos[tono]}`}
      role={tono === 'danger' ? 'alert' : 'status'}
      {...resto}
    >
      <Icono nombre={ICONOS[tono]} />
      <div>
        {titulo && <strong className={estilos.titulo}>{titulo}</strong>}
        <div>{children}</div>
      </div>
    </div>
  );
}
