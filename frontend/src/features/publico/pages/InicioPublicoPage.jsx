import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { obtenerInicioPublico } from '../../../api/publico.js';
import {
  Biblioteca,
  Icono,
  Logo,
  Portada,
  SiluetaLibros,
  Skeleton,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { MENSAJES } from '../../../utils/mensajes.js';
import estilos from './InicioPublicoPage.module.css';

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
  const { data, isPending, isError } = useQuery({
    queryKey: ['publico', 'inicio'],
    queryFn: () => obtenerInicioPublico(12),
    staleTime: 60_000,
  });
  const destacados = data?.destacados ?? [];
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
        <div className={estilos.portadaFondo}>
          <section className={estilos.portada} aria-labelledby="titulo-portada">
            <div className={estilos.texto}>
              <h1 id="titulo-portada" className={estilos.titulo}>
                <span>Pídalo acá.</span> <span className={estilos.acento}>Retírelo allá.</span>
              </h1>
              <p className={estilos.bajada}>
                Pida cualquiera de los {data ? `${cantidad(data.libros)} títulos` : 'títulos'} de la
                red y retírelo en la sede que le quede más cerca.
              </p>
              <div className={estilos.botones}>
                <Link to="/login" className={estilos.boton}>
                  Ingresar al sistema <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>
            <div className={estilos.vitrina}>
              <span className={estilos.mancha} aria-hidden="true" />
              <span className={estilos.anillo} aria-hidden="true" />
              <Biblioteca />
            </div>
            {data && (
              <dl className={estilos.cifras}>
                <div>
                  <Icono nombre="edificio" />
                  <dt>Sedes conectadas</dt>
                  <dd>{data.sedes_activas}</dd>
                </div>
                <div>
                  <Icono nombre="biblioteca" />
                  <dt>Títulos en catálogo</dt>
                  <dd>{cantidad(data.libros)}</dd>
                </div>
                <div>
                  <Icono nombre="libro" />
                  <dt>Ejemplares en la red</dt>
                  <dd>{cantidad(data.ejemplares)}</dd>
                </div>
              </dl>
            )}
          </section>
        </div>

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
            {isError && (
              <p className={estilos.explicacion}>
                No se pudieron cargar los libros más pedidos. Reintente más tarde.
              </p>
            )}
            {!isPending && !isError && destacados.length === 0 && (
              <p className={estilos.explicacion}>Todavía no hay préstamos para mostrar.</p>
            )}
            <ol className={estilos.grilla}>
              {destacados.map((libro, i) => (
                <li key={libro.libro_id} className={estilos.libro}>
                  {/* Los que completan la lista sin préstamos no llevan puesto. */}
                  {libro.pedidos > 0 && (
                    <span className={estilos.puesto}>
                      <span className="sr-only">Puesto </span>
                      {i + 1}
                    </span>
                  )}
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

      <SiluetaLibros />
      <footer className={estilos.pie}>
        <p className={estilos.pieMarca}>
          <span className={estilos.pieLinea} aria-hidden="true" />
          Red de Bibliotecas Públicas
          <span className={estilos.pieLinea} aria-hidden="true" />
        </p>
        <p className={estilos.pieTexto}>
          Pida cualquier libro de la red y retírelo en la sede que le quede más cerca.
        </p>
        <p className={estilos.pieCreditos}>{MENSAJES.sistemaCompleto} · UTN FRC 2026</p>
      </footer>
    </div>
  );
}
