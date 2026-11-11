import { Button, Modal } from '../../../components/index.js';

/** Otra persona modificó la sede: la única salida es recargar los datos vigentes. */
export default function ConflictoVersionDialog({ onRecargar }) {
  return (
    <Modal
      titulo="Otra persona modificó esta sede"
      onCerrar={onRecargar}
      acciones={
        <Button onClick={onRecargar} data-autofocus>
          Recargar
        </Button>
      }
    >
      <p style={{ margin: 0 }}>
        La sede cambió mientras la estaba viendo. Recargue para trabajar con la versión vigente; los
        cambios que no guardó se descartan.
      </p>
    </Modal>
  );
}
