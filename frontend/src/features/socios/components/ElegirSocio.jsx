import { useState } from 'react';
import { BusquedaConEspera, Button, Skeleton, Table } from '../../../components/index.js';
import { useSocios } from '../hooks/useSocios.js';
import EstadoSocioBadge from './EstadoSocioBadge.jsx';

/** Buscador de socio por número, documento o nombre (para préstamos y reservas en mostrador). */
export default function ElegirSocio({ elegido, onElegir }) {
  const [q, setQ] = useState('');
  const { data, isFetching } = useSocios({ q, size: 10 }, { enabled: q.length > 1 });
  if (elegido) {
    return (
      <p style={{ margin: 0 }}>
        {elegido.apellido}, {elegido.nombre} <span className="mono">{elegido.numero_socio}</span>{' '}
        <EstadoSocioBadge socio={elegido} />{' '}
        <Button variante="secondary" tamano="sm" onClick={() => onElegir(null)}>
          Cambiar
        </Button>
      </p>
    );
  }
  const columnas = [
    { clave: 'numero_socio', titulo: 'Número' },
    { clave: 'nombre', titulo: 'Socio', render: (s) => `${s.apellido}, ${s.nombre}` },
    { clave: 'documento', titulo: 'Documento', render: (s) => s.nro_documento },
    { clave: 'estado', titulo: 'Estado', render: (s) => <EstadoSocioBadge socio={s} /> },
    {
      clave: 'elegir',
      titulo: 'Acción',
      render: (s) => (
        <Button tamano="sm" variante="secondary" onClick={() => onElegir(s)}>
          Elegir
        </Button>
      ),
    },
  ];
  return (
    <>
      <BusquedaConEspera
        etiqueta="Buscar socio por número, documento o nombre"
        valor={q}
        onBuscar={setQ}
      />
      {isFetching && <Skeleton alto={48} />}
      {data && data.items.length === 0 && <p>No hay socios que coincidan.</p>}
      {data && data.items.length > 0 && (
        <Table
          etiqueta="Socios encontrados"
          columnas={columnas}
          filas={data.items}
          idDe={(s) => s.id}
        />
      )}
    </>
  );
}
