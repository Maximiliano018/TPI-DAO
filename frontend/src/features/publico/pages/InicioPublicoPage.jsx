import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { obtenerInicioPublico } from '../../../api/publico.js';
import { Logo, Portada, Skeleton } from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { MENSAJES } from '../../../utils/mensajes.js';
import estilos from './InicioPublicoPage.module.css';

const LOMOS = ['burdeos', 'bosque', 'marino', 'ocre', 'ciruela', 'petroleo'];
// Libros de pie del estante cuando todavía no llegaron los datos (o si el backend no responde).
const DE_RELLENO = ['Rayuela', 'Ficciones', 'El túnel', 'Facundo', 'Martín Fierro', 'El Aleph'];

/** Estante de la portada: los títulos más pedidos como lomos de pie, de alturas distintas. */
function Estante({ titulos }) {
  return (
    <div className={estilos.estante} aria-hidden="true">
      <div className={estilos.lomos}>
        {titulos.map((titulo, i) => (
          <span
            key={`${titulo}-${i}`}
            className={estilos.lomo}
            style={{
              '--c': `var(--lomo-${LOMOS[i % LOMOS.length]})`,
              '--alto': `${Math.min(235, Math.max(140, 60 + titulo.length * 9 + ((i * 17) % 24)))}px`,
              '--ancho': `${38 + ((i * 13) % 22)}px`,
              transform: i % 7 === 6 ? 'rotate(4deg)' : undefined,
            }}
          >
            <span className={estilos.textoLomo}>{titulo}</span>
          </span>
        ))}
      </div>
      <div className={estilos.tabla} />
    </div>
  );
}

/**
 * Inicio público: lo primero que ve cualquiera antes de ingresar. Muestra la red (sedes, libros y
 * ejemplares) y los libros más pedidos con su portada; arriba a la derecha, el acceso al sistema.
 */
export default function InicioPublicoPage() {
  useTituloDePagina('Bienvenida');
  const { data, isPending } = useQuery({
    queryKey: ['publico', 'inicio'],
    queryFn: () => obtenerInicioPublico(12),
    staleTime: 60_000,
  });
  const destacados = data?.destacados ?? [];
  const titulosEstante = destacados.length
    ? destacados.map((d) => d.titulo).slice(0, 14)
    : DE_RELLENO;

  return (
    <div className={estilos.pagina}>
      <header className={estilos.barra}>
        <span className={estilos.marca}>
          <Logo tamano={30} />
          {MENSAJES.sistema}
        </span>
        <Link to="/login" className={estilos.ingresar}>
          Ingresar
        </Link>
      </header>

      <main id="contenido">
        <section className={estilos.portada} aria-labelledby="titulo-portada">
          <div className={estilos.texto}>
            <p className={estilos.volanta}>Red de bibliotecas públicas</p>
            <h1 id="titulo-portada" className={estilos.titulo}>
              Todos los libros de la red, <em>a una sede</em> de distancia.
            </h1>
            <p className={estilos.bajada}>
              Pedí un libro en cualquier sede y retiralo en la que te quede más cerca.
            </p>
            {data && (
              <dl className={estilos.cifras}>
                <div>
                  <dt>sedes</dt>
                  <dd>{data.sedes_activas}</dd>
                </div>
                <div>
                  <dt>libros</dt>
                  <dd>{data.libros.toLocaleString('es-AR')}</dd>
                </div>
                <div>
                  <dt>ejemplares</dt>
                  <dd>{data.ejemplares.toLocaleString('es-AR')}</dd>
                </div>
              </dl>
            )}
            <Link to="/login" className={estilos.boton}>
              Ingresar al sistema <span aria-hidden="true">→</span>
            </Link>
          </div>
          <Estante titulos={titulosEstante} />
        </section>

        <section className={estilos.destacados} aria-labelledby="titulo-destacados">
          <h2 id="titulo-destacados" className={estilos.subtitulo}>
            Los más pedidos de la red
          </h2>
          <p className={estilos.explicacion}>
            Los libros que más se prestaron en las sedes durante los últimos meses.
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
        </section>
      </main>

      <footer className={estilos.pie}>
        {MENSAJES.sistemaCompleto} · UTN FRC 2026. Portadas: Open Library.
      </footer>
    </div>
  );
}
