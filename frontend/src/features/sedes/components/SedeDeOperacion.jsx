import { useState } from 'react';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { Card, Select, Skeleton } from '../../../components/index.js';
import { ROLES } from '../../../utils/roles.js';
import { useSedes } from '../hooks/useSedes.js';

/**
 * Sede en la que se registra una operación nueva (préstamo, remito). El bibliotecario opera en
 * la suya; el administrador, que opera en cualquier sede, la elige (el backend la exige).
 */
export function useSedeDeOperacion() {
  const { usuario } = useSesion();
  const esAdmin = usuario.rol === ROLES.ADMIN;
  const [elegida, setElegida] = useState(null);
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 }, { enabled: esAdmin });
  if (!esAdmin) {
    return { esAdmin, sedeId: usuario.sede_id, nombre: usuario.sede?.nombre, sedes, setElegida };
  }
  const sede = sedes.data?.items.find((s) => s.id === elegida);
  return { esAdmin, sedeId: elegida, nombre: sede?.nombre, sedes, setElegida };
}

/** Selector de la sede para el administrador; para el bibliotecario no muestra nada. */
export default function SedeDeOperacion({ control, titulo, etiqueta, onCambiar }) {
  const { esAdmin, sedeId, sedes, setElegida } = control;
  if (!esAdmin) return null;
  return (
    <Card titulo={titulo}>
      {sedes.isPending ? (
        <Skeleton alto={40} />
      ) : (
        <Select
          etiqueta={etiqueta}
          requerido
          value={sedeId ?? ''}
          onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : null;
            setElegida(id);
            onCambiar?.(id);
          }}
        >
          <option value="">Elegir sede…</option>
          {sedes.data?.items.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </Select>
      )}
    </Card>
  );
}
