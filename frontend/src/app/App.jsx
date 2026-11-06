import { Link, Navigate, Route, Routes } from 'react-router-dom';
import VersionPage from '../features/sistema/pages/VersionPage.jsx';

// Punto de entrada de la interfaz. Aquí se irán sumando providers, rutas y layout principal.
function Inicio() {
  return (
    <main>
      <h1>Sistema de Préstamos Interbibliotecarios</h1>
      <p>
        <Link to="/version">Ver versión y estado del sistema</Link>
      </p>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/version" element={<VersionPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
