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
import { formatearFecha, formatearMonto } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import { useMultas, useSaldarMulta } from '../hooks/useDevoluciones.js';

function Saldar({ multa, onCerrar }) {
  const saldar = useSaldarMulta();
  const { mostrar } = useToast();
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Saldar la multa de ${multa.socio}`}
      descripcion={`${formatearMonto(multa.monto_total)} por el préstamo ${multa.numero_prestamo}. El cobro se registra fuera del sistema; si era la única causa, el socio vuelve a estar habilitado.`}
      textoConfirmar="Marcar saldada"
      procesando={saldar.isPending}
      onConfirmar={() =>
        saldar.mutate(multa.id, {
          onSuccess: () => {
            mostrar('Multa saldada');
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

/** Multas por atraso: el personal ve las de la red y las salda; el socio ve las propias. */
export default function MultasPage() {
  const { tienePermiso } = useSesion();
  const esPersonal = tienePermiso(PERMISOS.MULTA_LEER);
  const titulo = esPersonal ? 'Multas' : 'Mis multas';
  useTituloDePagina(titulo);
  const { filtros, cambiar, limpiar, hayFiltros } = useFiltrosUrl();
  const page = Number(filtros.page) || 1;
  const size = Number(filtros.size) || 20;
  const { data, isPending, error, refetch } = useMultas({
    estado: filtros.estado,
    socio_id: filtros.socio_id,
    page,
    size,
  });
  const [aSaldar, setASaldar] = useState(null);
  const pendientes = data?.items.filter((m) => m.estado === 'PENDIENTE') ?? [];

  const columnas = [
    {
      clave: 'prestamo',
      titulo: 'Préstamo',
      render: (m) => (
        <Link to={`/prestamos/${m.prestamo_id}`} className="mono">
          {m.numero_prestamo}
        </Link>
      ),
    },
    ...(esPersonal
      ? [
          {
            clave: 'socio',
            titulo: 'Socio',
            render: (m) => <Link to={`/socios/${m.socio_id}`}>{m.socio}</Link>,
          },
        ]
      : []),
    { clave: 'libro', titulo: 'Libro' },
    { clave: 'dias', titulo: 'Días de atraso', render: (m) => m.dias_atraso },
    {
      clave: 'monto',
      titulo: 'Monto',
      render: (m) => (
        <span title={`${formatearMonto(m.monto_por_dia)} por día`}>
          {formatearMonto(m.monto_total)}
        </span>
      ),
    },
    {
      clave: 'fecha',
      titulo: 'Generada',
      render: (m) => formatearFecha(m.fecha_generacion),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      render: (m) => <EstadoBadge entidad="multa" estado={m.estado} />,
    },
    ...(tienePermiso(PERMISOS.MULTA_SALDAR)
      ? [
          {
            clave: 'acciones',
            titulo: 'Acciones',
            render: (m) =>
              m.estado === 'PENDIENTE' ? (
                <Button
                  tamano="sm"
                  aria-label={`Saldar la multa del préstamo ${m.numero_prestamo}`}
                  onClick={() => setASaldar(m)}
                >
                  Saldar
                </Button>
              ) : (
                `Saldada el ${formatearFecha(m.fecha_saldada)}`
              ),
          },
        ]
      : []),
  ];

  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion="Se generan al devolver fuera de término: días de atraso × monto por día."
      />
      {!esPersonal && pendientes.length > 0 && (
        <Alert tono="warning">
          Mientras tenga multas pendientes no puede pedir préstamos ni reservas. Acérquese a
          cualquier sede para saldarlas.
        </Alert>
      )}
      <FilterBar etiqueta="Filtros de multas" onLimpiar={limpiar} hayFiltros={hayFiltros}>
        <FiltroSelect
          etiqueta="Estado"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => cambiar({ estado })}
        >
          <option value="">Todas</option>
          {Object.entries(ESTADOS.multa).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FilterBar>
      {isPending && <Skeleton alto={160} />}
      {error && <ErrorState error={error} onReintentar={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState titulo={hayFiltros ? 'Ninguna multa coincide' : 'No hay multas'} />
      )}
      {data && data.items.length > 0 && (
        <>
          <Table etiqueta="Multas" columnas={columnas} filas={data.items} idDe={(m) => m.id} />
          <Pagination
            page={data.page}
            size={data.size}
            total={data.total}
            onPage={(p) => cambiar({ page: p })}
            onSize={(s) => cambiar({ size: s === 20 ? '' : s })}
          />
        </>
      )}
      {aSaldar && <Saldar multa={aSaldar} onCerrar={() => setASaldar(null)} />}
    </>
  );
}
