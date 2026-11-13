import { Link } from 'react-router-dom';
import { Card } from '../../../components/index.js';
import estilos from './Inicio.module.css';
import SedesDeLaRed from './SedesDeLaRed.jsx';

export default function InicioSocio() {
  return (
    <div className={estilos.pagina}>
      <Card titulo="Mi cuenta">
        <p style={{ margin: 0 }}>
          <Link to="/mis-datos">Ver mis datos y mi situación</Link>: préstamos, multas y reservas.
        </p>
      </Card>
      <SedesDeLaRed titulo="Sedes donde puede retirar y devolver" />
    </div>
  );
}
