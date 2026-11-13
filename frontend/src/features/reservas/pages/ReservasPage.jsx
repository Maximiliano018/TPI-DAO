import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroSelect,
  PageHeader,
  Pagination,
  Skeleton,
  Table,
  useToast,
} from '../../../components/index.js';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS } from '../../../utils/estados.js';
import { formatearFecha, formatearFechaHora } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import { useCancelarReserva, useReservas, useRetirarReserva } from '../hooks/useReservas.js';

function Accion({ reserva, tipo, onCerrar }) {
  const cancelar = useCancelarReserva();
  const retirar = useRetirarReserva();
  const mutacion = tipo === 'retirar' ? retirar : cancelar;
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`${tipo === 'retirar' ? 'Entregar' : 'Cancelar'} la reserva ${reserva.numero}`}
      descripcion={
        tipo === 'retirar'
          ? `Se entrega ${reserva.codigo_ejemplar} y empieza el préstamo.`
          : 'Si ya tenía un ejemplar asignado, pasa al siguiente de la cola.'
      }
      textoConfirmar={tipo === 'retirar' ? 'Entregar' : 'Cancelar reserva'}
      peligro={tipo !== 'retirar'}
      procesando={mutacion.isPending}
      onConfirmar={() =>
        mutacion.mutate(reserva.id, {
          onSuccess: () => {
            mostrar(tipo === 'retirar' ? 'Reserva entregada' : 'Reserva cancelada');
            onCerrar();
          },
          onError: setFallo,
        })
      }
      onCancelar={onCerrar}
    >
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** Reservas: el socio ve las propias con su lugar en la cola; el personal, todas. */
export default function ReservasPage() {
  const { usuario, tienePermiso } = useSesion();
  const esPersonal = tienePermiso(PERMISOS.RESERVA_LEER);
  const titulo = esPersonal ? 'Reservas' : 'Mis reservas';
  useTituloDePagina(titulo);
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const { data, isPending, error, refetch } = useReservas({
    estado: filtros.estado,
    libro_id: filtros.libro_id,
    page,
    size,
  });
  const [dialogo, setDialogo] = useState(null);

  const columnas = [
    { clave: 'numero', titulo: 'Número', render: (r) => <span className="mono">{r.numero}</span> },
    {
      clave: 'libro',
      titulo: 'Libro',
      render: (r) => <Link to={`/catalogo/${r.libro_id}`}>{r.libro}</Link>,
    },
    ...(esPersonal ? [{ clave: 'socio', titulo: 'Socio' }] : []),
    { clave: 'sede_retiro', titulo: 'Retira en' },
    { clave: 'fecha', titulo: 'Reservada', render: (r) => formatearFechaHora(r.fecha_reserva) },
    {
      clave: 'cola',
      titulo: 'Situación',
      render: (r) => {
        if (r.estado === 'PENDIENTE') return `Lugar ${r.posicion_en_cola} en la cola`;
        if (r.estado === 'DISPONIBLE_PARA_RETIRO') {
          return `Retirar hasta el ${formatearFecha(r.vencimiento_retiro)}`;
        }
        if (r.prestamo_id) return <Link to={`/prestamos/${r.prestamo_id}`}>Ver préstamo</Link>;
        return '—';
      },
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      render: (r) => <EstadoBadge entidad="reserva" estado={r.estado} />,
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      render: (r) => (
        <div className={estilos.acciones}>
          {r.estado === 'DISPONIBLE_PARA_RETIRO' &&
            tienePermiso(PERMISOS.RESERVA_REGISTRAR) &&
            usuario.sede_id === r.sede_retiro_id && (
              <Button tamano="sm" onClick={() => setDialogo({ reserva: r, tipo: 'retirar' })}>
                Entregar
              </Button>
            )}
          {['PENDIENTE', 'DISPONIBLE_PARA_RETIRO'].includes(r.estado) && (
            <Button
              tamano="sm"
              variante="secondary"
              aria-label={`Cancelar la reserva ${r.numero}`}
              onClick={() => setDialogo({ reserva: r, tipo: 'cancelar' })}
            >
              Cancelar
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion="Para reservar, abra un libro sin ejemplares disponibles en el catálogo."
      />
      <FilterBar etiqueta="Filtros de reservas" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todas</option>
          {Object.entries(ESTADOS.reserva).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>
      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && <EmptyState titulo="No hay reservas" />}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Reservas" columnas={columnas} filas={data.items} idDe={(r) => r.id} />
          <Pagination
            page={data.page}
            size={data.size}
            total={data.total}
            onPage={(p) => cambiar({ page: p })}
            onSize={(s) => cambiar({ size: s === 20 ? '' : s })}
          />
        </>
      )}
      {dialogo && <Accion {...dialogo} onCerrar={() => setDialogo(null)} />}
    </>
  );
}
