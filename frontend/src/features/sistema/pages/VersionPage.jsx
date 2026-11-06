import { useEffect, useState } from 'react';
import { obtenerVersionBackend } from '../../../api/version.js';

// __APP_VERSION__ la inyecta Vite desde package.json (ver vite.config.js).
const VERSION_FRONTEND = typeof __APP_VERSION__ === 'undefined' ? 'desconocida' : __APP_VERSION__;

export default function VersionPage() {
  const [backend, setBackend] = useState({ cargando: true });

  useEffect(() => {
    let activo = true;
    obtenerVersionBackend()
      .then((datos) => activo && setBackend({ datos }))
      .catch((error) => activo && setBackend({ error: error.message }));
    return () => {
      activo = false;
    };
  }, []);

  return (
    <main>
      <h1>Versión y estado del sistema</h1>
      <table>
        <thead>
          <tr>
            <th scope="col">Servicio</th>
            <th scope="col">Estado</th>
            <th scope="col">Versión</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Frontend</th>
            <td>En línea</td>
            <td>{VERSION_FRONTEND}</td>
          </tr>
          <tr>
            <th scope="row">Backend</th>
            {backend.cargando && <td colSpan={2}>Consultando…</td>}
            {backend.error && (
              <>
                <td role="alert">Sin conexión</td>
                <td>{backend.error}</td>
              </>
            )}
            {backend.datos && (
              <>
                <td>{backend.datos.estado === 'ok' ? 'En línea' : backend.datos.estado}</td>
                <td>{backend.datos.version}</td>
              </>
            )}
          </tr>
        </tbody>
      </table>
    </main>
  );
}
