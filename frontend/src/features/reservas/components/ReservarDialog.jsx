import { useState } from 'react';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { Alert, ConfirmDialog, Select, useToast } from '../../../components/index.js';
import { mensajeDeError } from '../../../utils/errores.js';
import { ROLES } from '../../../utils/roles.js';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import ElegirSocio from '../../socios/components/ElegirSocio.jsx';
import { useCrearReserva } from '../hooks/useReservas.js';

/**
 * Reservar un libro: el socio elige la sede de retiro; el bibliotecario reserva en nombre de un
 * socio para retirar en su sede. El backend rechaza si hay disponibles en esa sede.
 */
export default function ReservarDialog({ libro, onCerrar }) {
  const { usuario } = useSesion();
  const esSocio = usuario.rol === ROLES.SOCIO;
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 });
  const crear = useCrearReserva();
  const { mostrar } = useToast();
  const [sedeId, setSedeId] = useState(esSocio ? '' : String(usuario.sede_id ?? ''));
  const [socio, setSocio] = useState(null);
  const [fallo, setFallo] = useState(null);
  const listo = sedeId !== '' && (esSocio || socio);

  return (
    <ConfirmDialog
      titulo={`Reservar «${libro.titulo}»`}
      descripcion="Entra a la cola de espera: cuando se libere un ejemplar, se lo asigna al primero."
      textoConfirmar="Reservar"
      procesando={crear.isPending}
      deshabilitarConfirmar={!listo}
      onConfirmar={() => {
        setFallo(null);
        crear.mutate(
          {
            libro_id: libro.id,
            sede_retiro_id: Number(sedeId),
            ...(esSocio ? {} : { socio_id: socio.id }),
          },
          {
            onSuccess: (r) => {
              mostrar(`Reserva ${r.numero} registrada: lugar ${r.posicion_en_cola} en la cola`);
              onCerrar();
            },
            onError: setFallo,
          },
        );
      }}
      onCancelar={onCerrar}
    >
      {!esSocio && <ElegirSocio elegido={socio} onElegir={setSocio} />}
      <Select
        etiqueta="Sede de retiro"
        requerido
        value={sedeId}
        onChange={(e) => setSedeId(e.target.value)}
      >
        <option value="">Elija la sede</option>
        {(sedes.data?.items ?? []).map((s) => (
          <option key={s.id} value={s.id}>
            {s.nombre}
          </option>
        ))}
      </Select>
      {fallo && <Alert tono="danger">{mensajeDeError(fallo)}</Alert>}
    </ConfirmDialog>
  );
}
