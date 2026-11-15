import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  FilterBar,
  FiltroSelect,
  Input,
  PageHeader,
  Pagination,
  Select,
  Skeleton,
  Table,
  useToast,
} from '../../../components/index.js';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS, MEDIOS_DE_MOSTRADOR, MEDIOS_DE_PAGO } from '../../../utils/estados.js';
import { formatearFecha, formatearMonto } from '../../../utils/formato.js';
import { PERMISOS } from '../../../utils/roles.js';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import BotonComprobante from '../components/BotonComprobante.jsx';
import estilos from '../../sedes/components/Sedes.module.css';
import FiltroSocio from '../../socios/components/FiltroSocio.jsx';
import { useIniciarPago, useMultas, useSaldarMulta } from '../hooks/useDevoluciones.js';

function Saldar({ multa, onCerrar }) {
  const saldar = useSaldarMulta();
  const { mostrar } = useToast();
  const [medio, setMedio] = useState('EFECTIVO');
  const [comprobante, setComprobante] = useState('');
  const [fallo, setFallo] = useState(null);
  return (
    <ConfirmDialog
      titulo={`Cobrar la multa de ${multa.socio}`}
      descripcion={`${formatearMonto(multa.monto_total)} por el préstamo ${multa.numero_prestamo}. Si era la única causa, el socio vuelve a estar habilitado.`}
      textoConfirmar="Registrar el cobro"
      procesando={saldar.isPending}
      onConfirmar={() =>
        saldar.mutate(
          { id: multa.id, medio, comprobante: comprobante.trim() },
          {
            onSuccess: () => {
              mostrar('Multa saldada');
              onCerrar();
            },
            onError: setFallo,
          },
        )
      }
      onCancelar={onCerrar}
    >
      {multa.pago_en_curso && (
        <Alert tono="warning">
          El socio inició un pago en línea: al cobrar en el mostrador se cancela.
        </Alert>
      )}
      <Select etiqueta="Medio de pago" value={medio} onChange={(e) => setMedio(e.target.value)}>
        {MEDIOS_DE_MOSTRADOR.map((valor) => (
          <option key={valor} value={valor}>
            {MEDIOS_DE_PAGO[valor]}
          </option>
        ))}
      </Select>
      <Input
        etiqueta="Comprobante (opcional)"
        ayuda="Número de cupón o de operación."
        maxLength={100}
        value={comprobante}
        onChange={(e) => setComprobante(e.target.value)}
      />
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}

/** El socio paga su multa en línea: va al checkout simulado (no hay cobro real). */
function PagarEnLinea({ multa }) {
  const iniciar = useIniciarPago();
  const navegar = useNavigate();
  const [fallo, setFallo] = useState(null);
  const enCurso = multa.pago_en_curso;
  return (
    <div className={estilos.acciones}>
      <Button
        tamano="sm"
        aria-label={`${enCurso ? 'Continuar el pago' : 'Pagar en línea'} de la multa del préstamo ${multa.numero_prestamo}`}
        cargando={iniciar.isPending}
        onClick={() => {
          setFallo(null);
          iniciar.mutate(multa.id, {
            onSuccess: (pago) => navegar(`/pagos/simulado?pago=${pago.id}`),
            onError: setFallo,
          });
        }}
      >
        {enCurso ? 'Continuar el pago' : 'Pagar en línea'}
      </Button>
      {fallo && <span role="alert">{mensajeDeError(fallo)}</span>}
    </div>
  );
}

function SituacionDelPago({ multa }) {
  if (multa.estado === 'SALDADA') {
    const medio = multa.pago ? MEDIOS_DE_PAGO[multa.pago.medio] : null;
    return (
      <div className={estilos.acciones}>
        <span>
          Saldada el {formatearFecha(multa.fecha_saldada)}
          {medio ? ` · ${medio}` : ''}
        </span>
        {multa.pago && <BotonComprobante pago={multa.pago} variante="secondary" tamano="sm" />}
      </div>
    );
  }
  return multa.pago_en_curso ? 'Pago en línea en curso' : 'Sin pagar';
}

/**
 * Multas por atraso: el personal ve las de la red (o las de un socio) y las salda; el socio ve
 * las propias.
 */
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
    { clave: 'pago', titulo: 'Pago', render: (m) => <SituacionDelPago multa={m} /> },
    ...(tienePermiso(PERMISOS.MULTA_SALDAR)
      ? [
          {
            clave: 'acciones',
            titulo: 'Acciones',
            render: (m) =>
              m.estado === 'PENDIENTE' && (
                <Button
                  tamano="sm"
                  aria-label={`Saldar la multa del préstamo ${m.numero_prestamo}`}
                  onClick={() => setASaldar(m)}
                >
                  Saldar
                </Button>
              ),
          },
        ]
      : []),
    ...(tienePermiso(PERMISOS.MULTA_PAGAR_PROPIA)
      ? [
          {
            clave: 'pagar',
            titulo: 'Acciones',
            render: (m) => m.estado === 'PENDIENTE' && <PagarEnLinea multa={m} />,
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
          Mientras tenga multas pendientes no puede pedir préstamos ni reservas. Puede pagarlas en
          línea o en el mostrador de cualquier sede.
        </Alert>
      )}
      {esPersonal && (
        <FiltroSocio
          socioId={filtros.socio_id}
          onCambiar={(socioId) => cambiar({ socio_id: socioId })}
        />
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
