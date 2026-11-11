import { Breadcrumb, Button, ErrorState, PageHeader, Skeleton } from '../../../components/index.js';
import { useParams } from 'react-router-dom';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import UsuarioForm from '../components/UsuarioForm.jsx';
import { useUsuario } from '../hooks/useUsuarios.js';

/** Alta (`/usuarios/nuevo`) y edición (`/usuarios/:id/editar`) de personal. */
export default function UsuarioFormPage({ modo }) {
  const { id } = useParams();
  const editando = modo === 'editar';
  const titulo = editando ? 'Editar usuario' : 'Nuevo usuario';
  useTituloDePagina(titulo);
  const { data: usuario, isPending, error, refetch } = useUsuario(id, { enabled: editando });

  const migas = [{ texto: 'Usuarios', to: '/usuarios' }, { texto: titulo }];
  if (editando && isPending) return <Skeleton alto={240} />;
  if (editando && error) {
    return (
      <>
        <PageHeader titulo={titulo} migas={<Breadcrumb items={migas} />} />
        <ErrorState error={error} onReintentar={error.estado === 404 ? undefined : refetch} />
        <p>
          <Button to="/usuarios" variante="secondary">
            Volver a usuarios
          </Button>
        </p>
      </>
    );
  }
  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion={editando ? usuario.nombre : 'Cargue los datos del nuevo usuario del personal.'}
        migas={<Breadcrumb items={migas} />}
      />
      <UsuarioForm usuario={usuario} />
    </>
  );
}
