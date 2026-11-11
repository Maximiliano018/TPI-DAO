import Button from './Button.jsx';
import Modal from './Modal.jsx';

/**
 * Confirmación de una acción con su efecto descrito en una frase.
 * El botón principal se deshabilita mientras se procesa y el resultado se anuncia con `aria-live`.
 */
export default function ConfirmDialog({
  titulo,
  descripcion,
  textoConfirmar,
  peligro = false,
  procesando = false,
  deshabilitarConfirmar = false,
  onConfirmar,
  onCancelar,
  children,
}) {
  return (
    <Modal
      titulo={titulo}
      onCerrar={onCancelar}
      bloqueado={procesando}
      acciones={
        <>
          <Button variante="secondary" onClick={onCancelar} disabled={procesando}>
            Cancelar
          </Button>
          <Button
            variante={peligro ? 'danger' : 'primary'}
            onClick={onConfirmar}
            cargando={procesando}
            disabled={deshabilitarConfirmar}
          >
            {textoConfirmar}
          </Button>
        </>
      }
    >
      {descripcion && <p style={{ margin: 0 }}>{descripcion}</p>}
      {children}
      <p className="sr-only" aria-live="polite">
        {procesando ? 'Procesando…' : ''}
      </p>
    </Modal>
  );
}
