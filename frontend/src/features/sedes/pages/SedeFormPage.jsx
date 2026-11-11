import { useState } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { Breadcrumb, Button, ErrorState, PageHeader, Skeleton } from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import SedeForm from '../components/SedeForm.jsx';
import { useSede } from '../hooks/useSedes.js';

/** Alta (`/sedes/nueva`) y edición (`/sedes/:id/editar`). La edición no está disponible en baja. */
export default function SedeFormPage({ modo }) {
  const { id } = useParams();
  const editando = modo === 'editar';
  const titulo = editando ? 'Editar sede' : 'Nueva sede';
  useTituloDePagina(titulo);
  const { data: sede, isPending, error, refetch } = useSede(id, { enabled: editando });
  const [recarga, setRecarga] = useState(0);

  const migas = [
    { texto: 'Sedes', to: '/sedes' },
    ...(editando && sede ? [{ texto: sede.nombre, to: `/sedes/${sede.id}` }] : []),
    { texto: titulo },
  ];

  if (editando && isPending) return <Skeleton alto={240} />;
  if (editando && error) {
    return (
      <>
        <PageHeader titulo={titulo} migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
        <p>
          <Button to="/sedes" variante="secondary">
            Volver a sedes
          </Button>
        </p>
      </>
    );
  }
  if (editando && sede.estado === 'BAJA') {
    return (
      <Navigate
        to={`/sedes/${sede.id}`}
        replace
        state={{ aviso: 'Reactive la sede para poder editarla' }}
      />
    );
  }

  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion={editando ? sede.nombre : 'Cargue los datos de la nueva sede.'}
        migas={<Breadcrumb items={migas} />}
      />
      <SedeForm key={recarga} sede={sede} onRecargar={() => setRecarga((n) => n + 1)} />
    </>
  );
}
