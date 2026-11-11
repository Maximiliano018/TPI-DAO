import { mensajeDeError } from '../utils/errores.js';
import { MENSAJES } from '../utils/mensajes.js';
import Alert from './Alert.jsx';
import Button from './Button.jsx';

/** Error de carga con reintento. */
export default function ErrorState({ error, onReintentar }) {
  return (
    <Alert tono="danger">
      <p style={{ margin: '0 0 8px' }}>{mensajeDeError(error)}</p>
      {onReintentar && (
        <Button variante="secondary" tamano="sm" onClick={onReintentar}>
          {MENSAJES.reintentar}
        </Button>
      )}
    </Alert>
  );
}
