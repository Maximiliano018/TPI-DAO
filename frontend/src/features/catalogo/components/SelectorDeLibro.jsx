import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import { Combobox } from '../../../components/index.js';
import { PERMISOS } from '../../../utils/roles.js';
import { useLibro, useLibros } from '../hooks/useCatalogo.js';

const ESPERA_MS = 300;

const comoOpcion = (lb) => ({ id: lb.id, texto: lb.titulo, detalle: lb.autores.join(', ') });

/**
 * Elige el libro buscando en el servidor (título, autor o ISBN), así se llega a cualquier libro
 * del catálogo y no solo a los primeros. El libro elegido sigue entre las opciones aunque la
 * búsqueda cambie. Con `ofrecerAlta`, si no está, el administrador puede crearlo
 * (CU-CAT-02, A3). Lo usan el alta de ejemplar y el nuevo préstamo.
 *
 * @param {{valor?: number, onCambiar: (id: number|undefined) => void, error?: string, libroInicial?: number, ofrecerAlta?: boolean, requerido?: boolean}} props
 */
export default function SelectorDeLibro({
  valor,
  onCambiar,
  error,
  libroInicial,
  ofrecerAlta = false,
  requerido = true,
}) {
  const { tienePermiso } = useSesion();
  const [consulta, setConsulta] = useState('');
  const [q, setQ] = useState('');
  const [elegido, setElegido] = useState(null);
  const inicial = useLibro(libroInicial, { enabled: Boolean(libroInicial) });
  const resultados = useLibros({ q: q || undefined, size: 20 });

  useEffect(() => {
    const temporizador = setTimeout(() => setQ(consulta.trim()), ESPERA_MS);
    return () => clearTimeout(temporizador);
  }, [consulta]);

  const actual = elegido ?? (inicial.data?.id === valor ? inicial.data : null);
  const encontrados = resultados.data?.items ?? [];
  const opciones = [
    ...(actual && !encontrados.some((lb) => lb.id === actual.id) ? [actual] : []),
    ...encontrados,
  ].map(comoOpcion);

  return (
    <div>
      <Combobox
        etiqueta="Libro"
        requerido={requerido}
        opciones={opciones}
        filtrarLocalmente={false}
        onConsulta={setConsulta}
        valor={valor ?? ''}
        onCambiar={(id) => {
          // Al borrar el campo no queda ningún libro elegido entre las opciones.
          setElegido(id === '' ? null : (encontrados.find((lb) => lb.id === id) ?? actual));
          onCambiar(id === '' ? undefined : id);
        }}
        ayuda="Busque por título, autor o ISBN."
        error={error}
      />
      {ofrecerAlta && tienePermiso(PERMISOS.CATALOGO_ADMINISTRAR) && (
        <p style={{ margin: '4px 0 0' }}>
          ¿No está en el catálogo? <Link to="/catalogo/nuevo">Crear el libro</Link>
        </p>
      )}
    </div>
  );
}
