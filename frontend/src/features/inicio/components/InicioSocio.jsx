import estilos from './Inicio.module.css';
import SedesDeLaRed from './SedesDeLaRed.jsx';

export default function InicioSocio() {
  return (
    <div className={estilos.pagina}>
      <SedesDeLaRed titulo="Sedes donde puede retirar y devolver" />
    </div>
  );
}
