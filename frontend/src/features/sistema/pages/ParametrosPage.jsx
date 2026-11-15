import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  ErrorState,
  Input,
  PageHeader,
  Pagination,
  Skeleton,
  Table,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { formatearFechaHora } from '../../../utils/formato.js';
import inicio from '../../inicio/components/Inicio.module.css';
import {
  useActualizarParametro,
  useDetectarVencidos,
  useHistorialParametros,
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
          ayuda={
            parametro.actualizado_por
              ? `Modificado por ${parametro.actualizado_por.nombre} el ${formatearFechaHora(parametro.actualizado_en)}`
              : 'Valor inicial, sin cambios registrados'
          }
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

const COLUMNAS_HISTORIAL = [
  { clave: 'fecha', titulo: 'Fecha', render: (c) => formatearFechaHora(c.fecha_hora) },
  { clave: 'parametro', titulo: 'Parámetro', render: (c) => c.descripcion },
  {
    clave: 'cambio',
    titulo: 'Cambio',
    render: (c) => (
      <span className="mono">
        {c.valor_anterior} → {c.valor_nuevo}
      </span>
    ),
  },
  { clave: 'usuario', titulo: 'Usuario', render: (c) => c.usuario.nombre },
];

/** Auditoría: quién cambió cada parámetro, cuándo y de qué valor a cuál (RF-ACC-07). */
function HistorialDeCambios() {
  const [page, setPage] = useState(1);
  const { data, isPending, error, refetch } = useHistorialParametros({ page, size: 10 });
  if (isPending) return <Skeleton alto={120} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  if (data.items.length === 0) {
    return <p style={{ margin: 0 }}>Todavía no se cambió ningún parámetro.</p>;
  }
  return (
    <>
      <Table
        etiqueta="Historial de cambios de parámetros"
        columnas={COLUMNAS_HISTORIAL}
        filas={data.items}
        idDe={(c) => `${c.clave}-${c.fecha_hora}`}
      />
      <Pagination page={data.page} size={data.size} total={data.total} onPage={setPage} />
    </>
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
        <Card titulo="Historial de cambios">
          <HistorialDeCambios />
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
