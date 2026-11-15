import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  ErrorState,
  Input,
  PageHeader,
  Skeleton,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { formatearFechaHora, formatearMonto } from '../../../utils/formato.js';
import {
  digitos,
  formatearNumero,
  luhnValido,
  marca,
  vencimientoValido,
} from '../../../utils/tarjeta.js';
import BotonComprobante from '../components/BotonComprobante.jsx';
import estilos from '../components/PagoSimulado.module.css';
import { useIniciarPago, usePagarEnLinea, usePago } from '../hooks/useDevoluciones.js';

const FORMAS = {
  TARJETA_CREDITO: 'Tarjeta de crédito',
  TARJETA_DEBITO: 'Tarjeta de débito',
  DINERO_EN_CUENTA: 'Dinero en cuenta',
};
const PASOS = ['Forma de pago', 'Datos', 'Resultado'];
const TARJETA_VACIA = { numero: '', titular: '', vencimiento: '', cvv: '' };

/** Errores de los datos de tarjeta (se validan en el navegador y no se envían). */
function erroresDeTarjeta(t) {
  return {
    numero: luhnValido(t.numero) ? null : 'Revisá el número de la tarjeta.',
    titular: t.titular.trim().length >= 3 ? null : 'Ingresá el nombre como figura en la tarjeta.',
    vencimiento: vencimientoValido(t.vencimiento) ? null : 'Usá el formato MM/AA (no vencida).',
    cvv: /^\d{3,4}$/.test(t.cvv) ? null : 'El código tiene 3 o 4 dígitos.',
  };
}

function Resumen({ pago }) {
  return (
    <div className={estilos.resumen}>
      <span>
        Multa del préstamo <span className="mono">{pago.numero_prestamo}</span>
        {pago.dias_atraso ? ` · ${pago.dias_atraso} día(s) de atraso` : ''}
      </span>
      {pago.libro && <span>{pago.libro}</span>}
      <span className={estilos.total}>{formatearMonto(pago.monto)}</span>
    </div>
  );
}

function Resultado({ pago }) {
  const navegar = useNavigate();
  const iniciar = useIniciarPago();
  if (pago.estado === 'APROBADO') {
    return (
      <>
        <Alert tono="success">
          Pago aprobado: la multa quedó saldada. Comprobante{' '}
          <span className="mono">{pago.numero_comprobante}</span> del{' '}
          {formatearFechaHora(pago.acreditado_en)}.
        </Alert>
        <div className={estilos.acciones}>
          <BotonComprobante pago={pago} />
          <Button variante="secondary" to="/multas">
            Ir a mis multas
          </Button>
        </div>
      </>
    );
  }
  const textos = {
    RECHAZADO: `Pago rechazado: ${pago.motivo}. La multa sigue pendiente.`,
    CANCELADO: 'Este pago se canceló: la multa se cobró en el mostrador.',
  };
  return (
    <>
      <Alert tono={pago.estado === 'RECHAZADO' ? 'danger' : 'warning'}>{textos[pago.estado]}</Alert>
      <div className={estilos.acciones}>
        {pago.estado === 'RECHAZADO' && (
          <Button
            cargando={iniciar.isPending}
            onClick={() =>
              iniciar.mutate(pago.multa_id, {
                onSuccess: (nuevo) => navegar(`/pagos/simulado?pago=${nuevo.id}`),
              })
            }
          >
            Intentar de nuevo
          </Button>
        )}
        <Button variante="secondary" to="/multas">
          Ir a mis multas
        </Button>
      </div>
    </>
  );
}

/**
 * Checkout simulado del pago en línea (`/pagos/simulado?pago=ID`): forma de pago, datos y
 * resultado con su comprobante. Es una demostración: no hay cobro real. De la tarjeta solo se
 * envían los últimos 4 dígitos; el resto se valida en el navegador y se descarta.
 */
export default function PagoSimuladoPage() {
  useTituloDePagina('Pago en línea');
  const [params] = useSearchParams();
  const pagoId = params.get('pago');
  // Un pago nuevo (por ejemplo, al reintentar) arranca el checkout desde el principio.
  return <Checkout key={pagoId} pagoId={pagoId} />;
}

function Checkout({ pagoId }) {
  const pago = usePago(pagoId);
  const pagar = usePagarEnLinea();
  const [paso, setPaso] = useState(0);
  const [forma, setForma] = useState('TARJETA_CREDITO');
  const [tarjeta, setTarjeta] = useState(TARJETA_VACIA);
  const [intentoEnviar, setIntentoEnviar] = useState(false);
  const [fallo, setFallo] = useState(null);
  const actual = pagar.data ?? pago.data;
  const conTarjeta = forma !== 'DINERO_EN_CUENTA';
  const errores = erroresDeTarjeta(tarjeta);
  const valida = !conTarjeta || Object.values(errores).every((e) => e === null);
  const pasoVisible = actual && actual.estado !== 'PENDIENTE' ? 2 : paso;

  function cambiar(campo, valor) {
    setTarjeta((t) => ({ ...t, [campo]: valor }));
  }

  function confirmar(evento) {
    evento.preventDefault();
    setIntentoEnviar(true);
    if (!valida) return;
    setFallo(null);
    pagar.mutate(
      {
        id: pagoId,
        forma,
        tarjeta_ultimos4: conTarjeta ? digitos(tarjeta.numero).slice(-4) : null,
      },
      {
        // Los datos de la tarjeta se descartan apenas se confirma.
        onSettled: () => setTarjeta(TARJETA_VACIA),
        onError: setFallo,
      },
    );
  }

  const error = (campo) => (intentoEnviar ? errores[campo] : null);

  return (
    <>
      <PageHeader titulo="Pago en línea" />
      <Alert tono="info">Pago simulado para la demostración: no se cobra nada.</Alert>
      {pago.isPending && <Skeleton alto={160} />}
      {pago.error && <ErrorState error={pago.error} />}
      {actual && (
        <Card titulo="Pagar la multa">
          <ol className={estilos.pasos} aria-label="Pasos del pago">
            {PASOS.map((nombre, i) => (
              <li key={nombre} aria-current={i === pasoVisible ? 'step' : undefined}>
                {i + 1}. {nombre}
              </li>
            ))}
          </ol>
          <Resumen pago={actual} />

          {pasoVisible === 0 && (
            <>
              <fieldset className={estilos.opciones}>
                <legend>¿Cómo querés pagar?</legend>
                {Object.entries(FORMAS).map(([valor, texto]) => (
                  <label key={valor} className={estilos.opcion}>
                    <input
                      type="radio"
                      name="forma"
                      value={valor}
                      checked={forma === valor}
                      onChange={() => setForma(valor)}
                    />
                    {texto}
                  </label>
                ))}
              </fieldset>
              <Button onClick={() => setPaso(1)}>Continuar</Button>
            </>
          )}

          {pasoVisible === 1 && (
            <form onSubmit={confirmar} noValidate>
              {conTarjeta ? (
                <>
                  <div className={estilos.campos}>
                    <Input
                      etiqueta={`Número de la tarjeta${marca(tarjeta.numero) ? ` (${marca(tarjeta.numero)})` : ''}`}
                      requerido
                      inputMode="numeric"
                      autoComplete="off"
                      value={formatearNumero(tarjeta.numero)}
                      onChange={(e) => cambiar('numero', e.target.value)}
                      error={error('numero')}
                    />
                    <Input
                      etiqueta="Nombre del titular"
                      requerido
                      autoComplete="off"
                      value={tarjeta.titular}
                      onChange={(e) => cambiar('titular', e.target.value)}
                      error={error('titular')}
                    />
                    <Input
                      etiqueta="Vencimiento (MM/AA)"
                      requerido
                      inputMode="numeric"
                      autoComplete="off"
                      maxLength={5}
                      value={tarjeta.vencimiento}
                      onChange={(e) => cambiar('vencimiento', e.target.value)}
                      error={error('vencimiento')}
                    />
                    <Input
                      etiqueta="Código de seguridad"
                      requerido
                      type="password"
                      inputMode="numeric"
                      autoComplete="off"
                      maxLength={4}
                      value={tarjeta.cvv}
                      onChange={(e) => cambiar('cvv', e.target.value)}
                      error={error('cvv')}
                    />
                  </div>
                  <Alert tono="info">
                    Tarjetas de prueba: <span className="mono">4509 9535 6623 3704</span> se aprueba
                    y <span className="mono">4000 0000 0000 0002</span> se rechaza (con cualquier
                    titular, vencimiento futuro y código).
                  </Alert>
                </>
              ) : (
                <Alert tono="info">
                  Se debitará {formatearMonto(actual.monto)} del dinero en cuenta (simulado).
                </Alert>
              )}
              {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
              <div className={estilos.acciones}>
                <Button type="submit" cargando={pagar.isPending}>
                  Pagar {formatearMonto(actual.monto)}
                </Button>
                <Button variante="secondary" disabled={pagar.isPending} onClick={() => setPaso(0)}>
                  Volver
                </Button>
              </div>
            </form>
          )}

          {pasoVisible === 2 && <Resultado pago={actual} />}
        </Card>
      )}
    </>
  );
}
