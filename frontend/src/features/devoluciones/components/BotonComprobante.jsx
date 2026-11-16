import { useState } from 'react';
import { descargarComprobante } from '../../../api/devoluciones.js';
import { Alert, Button } from '../../../components/index.js';
import { guardarArchivo } from '../../../utils/descarga.js';
import { mensajeDeError } from '../../../utils/errores.js';

/** Descarga el comprobante en PDF de un pago aprobado. */
export default function BotonComprobante({ pago, variante = 'primary', tamano = 'md' }) {
  const [descargando, setDescargando] = useState(false);
  const [fallo, setFallo] = useState(null);
  return (
    <>
      <Button
        variante={variante}
        tamano={tamano}
        icono="comprobante"
        cargando={descargando}
        aria-label={`Descargar el comprobante ${pago.numero_comprobante ?? ''}`.trim()}
        onClick={async () => {
          setFallo(null);
          setDescargando(true);
          try {
            const { blob, nombre } = await descargarComprobante(pago.id);
            guardarArchivo(blob, nombre);
          } catch (error) {
            setFallo(error);
          } finally {
            setDescargando(false);
          }
        }}
      >
        {tamano === 'sm' ? 'Comprobante' : 'Descargar comprobante'}
      </Button>
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </>
  );
}
