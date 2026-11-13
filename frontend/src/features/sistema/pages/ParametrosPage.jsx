import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  ErrorState,
  Input,
  PageHeader,
  Skeleton,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import inicio from '../../inicio/components/Inicio.module.css';
import {
  useActualizarParametro,
  useDetectarVencidos,
  useParametros,
} from '../../prestamos/hooks/usePrestamos.js';
import { useVencerReservas } from '../../reservas/hooks/useReservas.js';

function Parametro({ parametro }) {
  const actualizar = useActualizarParametro();
  const { mostrar } = useToast();
  const [valor, setValor] = useState(parametro.valor);
  const [fallo, setFallo] = useState(null);
  return (
    <li className={inicio.elemento}>
      <div style={{ flex: 1 }}>
        <Input
          etiqueta={parametro.descripcion}
          value={valor}
          inputMode="decimal"
          error={fallo ? mensajeDeError(fallo) : undefined}
          onChange={(e) => setValor(e.target.value)}
        />
      </div>
      <Button
        variante="secondary"
        tamano="sm"
        disabled={valor === parametro.valor}
        cargando={actualizar.isPending}
        aria-label={`Guardar ${parametro.descripcion}`}
        onClick={() => {
          setFallo(null);
          actualizar.mutate(
            { clave: parametro.clave, valor },
            { onSuccess: () => mostrar('Parámetro guardado'), onError: setFallo },
          );
        }}
      >
        Guardar
      </Button>
    </li>
  );
}

/** Parámetros de negocio (plazos, límites y montos) y tareas del sistema (administrador). */
export default function ParametrosPage() {
  useTituloDePagina('Parámetros');
  const { data, isPending, error, refetch } = useParametros();
  const detectar = useDetectarVencidos();
  const vencer = useVencerReservas();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <>
      <PageHeader
        titulo="Parámetros"
        descripcion="Los cambios rigen desde la siguiente operación; las multas ya emitidas no cambian."
      />
      <div className={inicio.pagina}>
        <Card titulo="Valores vigentes">
          {isPending && <Skeleton alto={160} />}
          {error && <ErrorState error={error} onReintentar={refetch} />}
          {data && (
            <ul className={inicio.lista}>
              {data.map((p) => (
                <Parametro key={p.clave} parametro={p} />
              ))}
            </ul>
          )}
        </Card>
        <Card titulo="Tareas del sistema">
          <p style={{ marginTop: 0 }}>
            La detección de préstamos vencidos y el vencimiento de reservas corren solos todos los
            días; se pueden ejecutar ahora.
          </p>
          {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
          <Button
            variante="secondary"
            cargando={detectar.isPending}
            onClick={() =>
              detectar.mutate(undefined, {
                onSuccess: (r) => mostrar(`Préstamos marcados como vencidos: ${r.cambios}`),
                onError: setFallo,
              })
            }
          >
            Detectar vencidos ahora
          </Button>{' '}
          <Button
            variante="secondary"
            cargando={vencer.isPending}
            onClick={() =>
              vencer.mutate(undefined, {
                onSuccess: (r) => mostrar(`Reservas vencidas: ${r.cambios}`),
                onError: setFallo,
              })
            }
          >
            Vencer reservas no retiradas
          </Button>
        </Card>
      </div>
    </>
  );
}
