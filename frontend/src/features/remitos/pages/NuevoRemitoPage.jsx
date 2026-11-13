import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  PageHeader,
  Select,
  Skeleton,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import inicio from '../../inicio/components/Inicio.module.css';
import { useEjemplares } from '../../catalogo/hooks/useCatalogo.js';
import { useGenerarRemito, usePrestamos } from '../../prestamos/hooks/usePrestamos.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';

/** Envío: préstamos entre sedes solicitados que salen de esta sede, agrupados por destino. */
function LineasDeEnvio({ sedeId, destinoId, onDestino, elegidos, onElegidos }) {
  const { data, isPending, error, refetch } = usePrestamos({
    estado: 'SOLICITADO',
    tipo: 'INTERBIBLIOTECARIO',
    size: 100,
  });
  if (isPending) return <Skeleton alto={96} />;
  if (error) return <ErrorState error={error} onReintentar={refetch} />;
  const pendientes = data.items.filter((p) => p.sede_origen_id === sedeId);
  if (pendientes.length === 0) {
    return <EmptyState titulo="No hay préstamos esperando envío desde su sede" />;
  }
  const destinos = [...new Map(pendientes.map((p) => [p.sede_destino_id, p.sede_destino]))];
  const delDestino = pendientes.filter((p) => p.sede_destino_id === destinoId);
  return (
    <>
      <Select
        etiqueta="Sede destino"
        requerido
        value={destinoId ?? ''}
        onChange={(e) => {
          onDestino(e.target.value ? Number(e.target.value) : null);
          onElegidos([]);
        }}
      >
        <option value="">Elija la sede destino</option>
        {destinos.map(([id, nombre]) => (
          <option key={id} value={id}>
            {nombre}
          </option>
        ))}
      </Select>
      {delDestino.map((p) => (
        <Checkbox
          key={p.id}
          etiqueta={`${p.numero} · ${p.codigo_ejemplar} · ${p.libro} (para ${p.socio})`}
          checked={elegidos.some((x) => x.prestamo_id === p.id)}
          onChange={(e) =>
            onElegidos(
              e.target.checked
                ? [...elegidos, { ejemplar_id: p.ejemplar_id, prestamo_id: p.id }]
                : elegidos.filter((x) => x.prestamo_id !== p.id),
            )
          }
        />
      ))}
    </>
  );
}

/** Traslado: ejemplares disponibles de esta sede hacia otra sede activa. */
function LineasDeTraslado({ sedeId, destinoId, onDestino, elegidos, onElegidos }) {
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 });
  const ejemplares = useEjemplares({ sede_id: sedeId, estado: 'DISPONIBLE', size: 100 });
  if (sedes.isPending || ejemplares.isPending) return <Skeleton alto={96} />;
  if (sedes.error || ejemplares.error)
    return <ErrorState error={sedes.error ?? ejemplares.error} />;
  const propios = ejemplares.data.items.filter(
    (e) => e.sede_propietaria_id === sedeId && e.sede_actual_id === sedeId,
  );
  return (
    <>
      <Select
        etiqueta="Sede destino"
        requerido
        value={destinoId ?? ''}
        onChange={(e) => onDestino(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Elija la sede destino</option>
        {sedes.data.items
          .filter((s) => s.id !== sedeId)
          .map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
      </Select>
      {propios.length === 0 && <p>No hay ejemplares disponibles en su sede.</p>}
      {propios.map((e) => (
        <Checkbox
          key={e.id}
          etiqueta={`${e.codigo_inventario} · ${e.libro}`}
          checked={elegidos.some((x) => x.ejemplar_id === e.id)}
          onChange={(ev) =>
            onElegidos(
              ev.target.checked
                ? [...elegidos, { ejemplar_id: e.id }]
                : elegidos.filter((x) => x.ejemplar_id !== e.id),
            )
          }
        />
      ))}
    </>
  );
}

/** Generar un remito desde la sede del bibliotecario: envío de préstamos o traslado. */
export default function NuevoRemitoPage() {
  useTituloDePagina('Nuevo remito');
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const generar = useGenerarRemito();
  const [motivo, setMotivo] = useState('ENVIO');
  const [destinoId, setDestinoId] = useState(null);
  const [elegidos, setElegidos] = useState([]);
  const [observaciones, setObservaciones] = useState('');
  const [fallo, setFallo] = useState(null);
  const migas = [{ texto: 'Remitos', to: '/remitos' }, { texto: 'Nuevo remito' }];
  const Lineas = motivo === 'ENVIO' ? LineasDeEnvio : LineasDeTraslado;

  function confirmar() {
    setFallo(null);
    generar.mutate(
      {
        sede_destino_id: destinoId,
        motivo,
        lineas: elegidos,
        observaciones: observaciones || null,
      },
      {
        onSuccess: (remito) => {
          mostrar(`Remito ${remito.numero} generado`);
          navegar(`/remitos/${remito.id}`);
        },
        onError: setFallo,
      },
    );
  }

  return (
    <>
      <PageHeader
        titulo="Nuevo remito"
        descripcion={`Sale de ${usuario.sede?.nombre ?? 'su sede'}. Todos los ejemplares van al mismo destino.`}
        migas={<Breadcrumb items={migas} />}
      />
      <div className={inicio.pagina}>
        {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
        <Card titulo="Motivo">
          <Select
            etiqueta="Motivo"
            value={motivo}
            onChange={(e) => {
              setMotivo(e.target.value);
              setDestinoId(null);
              setElegidos([]);
            }}
          >
            <option value="ENVIO">Envío de préstamos a otra sede</option>
            <option value="TRASLADO">Traslado definitivo de ejemplares</option>
          </Select>
        </Card>
        <Card titulo="Ejemplares">
          <Lineas
            sedeId={usuario.sede_id}
            destinoId={destinoId}
            onDestino={setDestinoId}
            elegidos={elegidos}
            onElegidos={setElegidos}
          />
        </Card>
        <Card titulo="Observaciones">
          <Textarea
            etiqueta="Observaciones (opcional)"
            rows={2}
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
        </Card>
        <div>
          <Button
            disabled={!destinoId || elegidos.length === 0}
            cargando={generar.isPending}
            onClick={confirmar}
          >
            Generar remito ({elegidos.length})
          </Button>
        </div>
      </div>
    </>
  );
}
