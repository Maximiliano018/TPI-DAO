import estilos from './PageHeader.module.css';

/** Encabezado de pantalla: migas opcionales, título, descripción y acciones. */
export default function PageHeader({ titulo, descripcion, migas, acciones, children }) {
  return (
    <header className={estilos.encabezado}>
      {migas}
      <div className={estilos.fila}>
        <div>
          <h1 className={estilos.titulo} tabIndex={-1} data-page-title>
            {titulo}
          </h1>
          {descripcion && <p className={estilos.descripcion}>{descripcion}</p>}
          {children}
        </div>
        {acciones && <div className={estilos.acciones}>{acciones}</div>}
      </div>
    </header>
  );
}
