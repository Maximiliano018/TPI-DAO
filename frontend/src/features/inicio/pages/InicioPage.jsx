import { useSesion } from '../../../auth/SesionContext.jsx';
import { PageHeader } from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { ROLES } from '../../../utils/roles.js';
import InicioAdministrador from '../components/InicioAdministrador.jsx';
import InicioBibliotecario from '../components/InicioBibliotecario.jsx';
import InicioSocio from '../components/InicioSocio.jsx';

const POR_ROL = {
  [ROLES.ADMIN]: InicioAdministrador,
  [ROLES.BIBLIOTECARIO]: InicioBibliotecario,
  [ROLES.SOCIO]: InicioSocio,
};

/** Inicio: el contenido depende del rol; cada tarjeta resuelve sus propios estados. */
export default function InicioPage() {
  const { usuario } = useSesion();
  useTituloDePagina('Inicio');
  const Contenido = POR_ROL[usuario.rol] ?? InicioSocio;
  return (
    <>
      <PageHeader titulo="Inicio" descripcion={`Hola, ${usuario.nombre}.`} />
      <Contenido usuario={usuario} />
    </>
  );
}
