import { useParams } from 'react-router-dom';
import { Breadcrumb, Button, ErrorState, PageHeader, Skeleton } from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import SocioForm from '../components/SocioForm.jsx';
import { useSocio } from '../hooks/useSocios.js';

/** Alta (`/socios/nuevo`) y edición (`/socios/:id/editar`) de un socio. */
export default function SocioFormPage({ modo }) {
  const { id } = useParams();
  const editando = modo === 'editar';
  const titulo = editando ? 'Editar socio' : 'Nuevo socio';
  useTituloDePagina(titulo);
  const { data: socio, isPending, error, refetch } = useSocio(id, { enabled: editando });

  const migas = [{ texto: 'Socios', to: '/socios' }, { texto: titulo }];
  if (editando && isPending) return <Skeleton alto={240} />;
  if (editando && error) {
    return (
      <>
        <PageHeader titulo={titulo} migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
        <p>
          <Button to="/socios" variante="secondary">
            Volver a socios
          </Button>
        </p>
      </>
    );
  }
  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion={
          editando
            ? `${socio.nombre} ${socio.apellido} · socio ${socio.numero_socio}`
            : 'El sistema busca duplicados por documento y por nombre con fecha de nacimiento.'
        }
        migas={<Breadcrumb items={migas} />}
      />
      <SocioForm socio={socio} />
    </>
  );
}
