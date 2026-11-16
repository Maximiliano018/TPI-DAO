import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { obtenerInicioPublico } from '../../../api/publico.js';
import { Estante, Logo, Portada, Skeleton } from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { MENSAJES } from '../../../utils/mensajes.js';
import estilos from './InicioPublicoPage.module.css';

// Libros de pie del estante cuando todavía no llegaron los datos (o si el backend no responde).
const DE_RELLENO = ['Rayuela', 'Ficciones', 'El túnel', 'Facundo', 'Martín Fierro', 'El Aleph'];

/** Marca del sistema: nombre en mayúscula gruesa y la red debajo. */
export function Marca() {
  return (
    <span className={estilos.marca}>
      <Logo tamano={30} />
      <span className={estilos.sistema}>Red de Bibliotecas Públicas</span>
    </span>
  );
}

/**
 * Inicio público: lo primero que ve cualquiera antes de ingresar. El lema, el estante con los
 * libros más pedidos, las cifras de la red y, en la franja oscura, los más pedidos con su portada.
 */
export default function InicioPublicoPage() {
  useTituloDePagina('Bienvenida');
  const { data, isPending } = useQuery({
    queryKey: ['publico', 'inicio'],
    queryFn: () => obtenerInicioPublico(12),
    staleTime: 60_000,
  });
  const destacados = data?.destacados ?? [];
  const titulosEstante = destacados.length ? destacados.map((d) => d.titulo) : DE_RELLENO;
  const cantidad = (n) => n.toLocaleString('es-AR');

  return (
    <div className={estilos.pagina}>
      <header className={estilos.barra}>
        <Marca />
        <Link to="/login" className={estilos.ingresar}>
          Ingresar
        </Link>
      </header>

      <main id="contenido">
        <section className={estilos.portada} aria-labelledby="titulo-portada">
          <h1 id="titulo-portada" className={estilos.titulo}>
            <span>Pedilo acá.</span> <span className={estilos.acento}>Retiralo allá.</span>
          </h1>
          <div className={estilos.fila}>
            <p className={estilos.bajada}>
              Pedí cualquiera de los {data ? `${cantidad(data.libros)} títulos` : 'títulos'} de la
              red en la sede que quieras y retiralo en la que te quede más cerca.
            </p>
            <div className={estilos.botones}>
              <Link to="/login" className={estilos.boton}>
                Ingresar al sistema <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
          <p className={estilos.volanta}>El estante de la red</p>
          <Estante titulos={titulosEstante} />
          {data && (
            <dl className={estilos.cifras}>
              <div>
                <dt>Sedes conectadas</dt>
                <dd>{data.sedes_activas}</dd>
              </div>
              <div>
                <dt>Títulos en catálogo</dt>
                <dd>{cantidad(data.libros)}</dd>
              </div>
              <div>
                <dt>Ejemplares para prestar</dt>
                <dd>{cantidad(data.ejemplares)}</dd>
              </div>
            </dl>
          )}
        </section>

        <section
          id="mas-pedidos"
          className={estilos.destacados}
          aria-labelledby="titulo-destacados"
        >
          <div className={estilos.contenido}>
            <h2 id="titulo-destacados" className={estilos.subtitulo}>
              Los más pedidos
            </h2>
            <p className={estilos.explicacion}>
              Lo que más se prestó en las sedes durante los últimos meses.
            </p>
            {isPending && <Skeleton alto={260} />}
            {!isPending && destacados.length === 0 && (
              <p className={estilos.explicacion}>Pronto vas a ver acá los libros más pedidos.</p>
            )}
            <ol className={estilos.grilla}>
              {destacados.map((libro, i) => (
                <li key={libro.libro_id} className={estilos.libro}>
                  <span className={estilos.puesto}>
                    <span className="sr-only">Puesto </span>
                    {i + 1}
                  </span>
                  <Portada
                    titulo={libro.titulo}
                    autores={libro.autores}
                    portadaUrl={libro.portada_url}
                    tamano="mediana"
                  />
                  <h3 className={estilos.tituloLibro}>{libro.titulo}</h3>
                  <p className={estilos.autor}>{libro.autores.join(', ')}</p>
                  {libro.pedidos > 0 && (
                    <p className={estilos.pedidos}>
                      {libro.pedidos} {libro.pedidos === 1 ? 'préstamo' : 'préstamos'}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </section>
      </main>

      <footer className={estilos.pie}>
        {MENSAJES.sistemaCompleto} · UTN FRC 2026. Portadas: Open Library.
      </footer>
    </div>
  );
}
