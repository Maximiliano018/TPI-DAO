import { Link } from 'react-router-dom';
import { Button, Modal } from '../../../components/index.js';

/** Ya hay una sede en esa dirección: se puede corregir o confirmar que es intencional. */
export default function DireccionDuplicadaDialog({ error, procesando, onCorregir, onConfirmar }) {
  const sedes = error.detalles.map((d) => d.sede).filter(Boolean);
  return (
    <Modal
      titulo="Ya hay una sede en esa dirección"
      onCerrar={onCorregir}
      bloqueado={procesando}
      acciones={
        <>
          <Button variante="secondary" onClick={onCorregir} disabled={procesando} data-autofocus>
            Volver y corregir
          </Button>
          <Button onClick={onConfirmar} cargando={procesando}>
            Guardar de todas formas
          </Button>
        </>
      }
    >
      <p style={{ marginTop: 0 }}>
        Puede corregir la dirección o confirmar que es intencional (por ejemplo, dos sedes en el
        mismo edificio).
      </p>
      <ul>
        {sedes.map((sede) => (
          <li key={sede.id}>
            <Link to={`/sedes/${sede.id}`}>{sede.nombre}</Link> ({sede.codigo})
          </li>
        ))}
      </ul>
    </Modal>
  );
}
