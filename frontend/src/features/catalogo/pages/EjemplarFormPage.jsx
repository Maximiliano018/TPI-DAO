import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useSesion } from '../../../auth/SesionContext.jsx';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Combobox,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Skeleton,
  Textarea,
  useToast,
} from '../../../components/index.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { erroresPorCampo, mensajeDeError } from '../../../utils/errores.js';
import { ESTADOS_FISICOS } from '../../../utils/estados.js';
import { PERMISOS, ROLES } from '../../../utils/roles.js';
import estilos from '../../sedes/components/Sedes.module.css';
import { useSedes } from '../../sedes/hooks/useSedes.js';
import { esquemaEjemplar } from '../esquema.js';
import { useCrearEjemplar, useLibro, useLibros } from '../hooks/useCatalogo.js';

const CAMPOS = ['libro_id', 'codigo_inventario', 'estado_fisico', 'observaciones', 'sede_id'];
const comoNumero = (valor) => (valor === '' ? undefined : Number(valor));
const ESPERA_MS = 300;

const comoOpcion = (lb) => ({ id: lb.id, texto: lb.titulo, detalle: lb.autores.join(', ') });

/**
 * Elige el libro buscando en el servidor (título, autor o ISBN), así se llega a cualquier libro
 * del catálogo y no solo a los primeros. El libro elegido sigue entre las opciones aunque la
 * búsqueda cambie. Si no está, el administrador puede crearlo (CU-CAT-02, A3).
 */
function SelectorDeLibro({ valor, onCambiar, error, libroInicial }) {
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
        requerido
        opciones={opciones}
        filtrarLocalmente={false}
        onConsulta={setConsulta}
        valor={valor ?? ''}
        onCambiar={(id) => {
          setElegido(encontrados.find((lb) => lb.id === id) ?? actual);
          onCambiar(id === '' ? undefined : id);
        }}
        ayuda="Busque por título, autor o ISBN."
        error={error}
      />
      {tienePermiso(PERMISOS.CATALOGO_ADMINISTRAR) && (
        <p style={{ margin: '4px 0 0' }}>
          ¿No está en el catálogo? <Link to="/catalogo/nuevo">Crear el libro</Link>
        </p>
      )}
    </div>
  );
}

/** Alta de un ejemplar: el bibliotecario lo carga en su sede; el administrador elige la sede. */
export default function EjemplarFormPage() {
  useTituloDePagina('Nuevo ejemplar');
  const { usuario } = useSesion();
  const [params] = useSearchParams();
  const esAdmin = usuario.rol === ROLES.ADMIN;
  const sedes = useSedes({ estado: 'ACTIVA', orden: 'nombre', size: 100 }, { enabled: esAdmin });
  const migas = [{ texto: 'Ejemplares', to: '/ejemplares' }, { texto: 'Nuevo ejemplar' }];
  const cargando = esAdmin && sedes.isPending;
  const error = esAdmin ? sedes.error : null;
  return (
    <>
      <PageHeader
        titulo="Nuevo ejemplar"
        descripcion="La copia física queda disponible en la sede elegida."
        migas={<Breadcrumb items={migas} />}
      />
      {cargando && <Skeleton alto={240} />}
      {!cargando && error && <ErrorState error={error} />}
      {!cargando && !error && (
        <Formulario
          sedesActivas={esAdmin ? sedes.data.items : null}
          sedePropia={usuario.sede}
          libroInicial={params.get('libro_id') ? Number(params.get('libro_id')) : undefined}
        />
      )}
    </>
  );
}

function Formulario({ sedesActivas, sedePropia, libroInicial }) {
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const crear = useCrearEjemplar();
  const [errorGeneral, setErrorGeneral] = useState(null);
  const {
    control,
    register,
    handleSubmit,
    setError,
    setFocus,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaEjemplar),
    defaultValues: {
      libro_id: libroInicial,
      codigo_inventario: '',
      estado_fisico: 'BUENO',
      observaciones: '',
      sede_id: undefined,
    },
  });

  function enviar(datos) {
    setErrorGeneral(null);
    crear.mutate(
      {
        libro_id: datos.libro_id,
        codigo_inventario: datos.codigo_inventario,
        estado_fisico: datos.estado_fisico,
        observaciones: datos.observaciones || null,
        sede_id: sedesActivas ? (datos.sede_id ?? null) : null,
      },
      {
        onSuccess: (ejemplar) => {
          mostrar(`Ejemplar ${ejemplar.codigo_inventario} cargado`);
          navegar(`/catalogo/${ejemplar.libro_id}`);
        },
        onError: (error) => {
          const porCampo = erroresPorCampo(error);
          if (error.codigo === 'EJEMPLAR_CODIGO_DUPLICADO') {
            porCampo.codigo_inventario = mensajeDeError(error);
          }
          const campos = CAMPOS.filter((c) => porCampo[c]);
          for (const c of campos) setError(c, { message: porCampo[c] });
          if (campos.length > 0 && campos[0] !== 'libro_id') setFocus(campos[0]);
          else if (campos.length === 0) setErrorGeneral(mensajeDeError(error));
        },
      },
    );
  }

  return (
    <form className={estilos.formulario} noValidate onSubmit={handleSubmit(enviar)}>
      {errorGeneral && <Alert tono="danger">{errorGeneral}</Alert>}
      <Card titulo="Ejemplar">
        <div className={estilos.grupo}>
          <Controller
            control={control}
            name="libro_id"
            render={({ field }) => (
              <SelectorDeLibro
                valor={field.value}
                onCambiar={field.onChange}
                error={errors.libro_id?.message}
                libroInicial={libroInicial}
              />
            )}
          />
          <Input
            etiqueta="Código de inventario"
            requerido
            autoComplete="off"
            ayuda="Único en toda la red, por ejemplo CEN-000123."
            error={errors.codigo_inventario?.message}
            {...register('codigo_inventario')}
          />
          <Select etiqueta="Estado físico" requerido {...register('estado_fisico')}>
            {Object.entries(ESTADOS_FISICOS).map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </Select>
          {sedesActivas ? (
            <Select
              etiqueta="Sede"
              requerido
              ayuda="Solo se ofrecen sedes activas."
              error={errors.sede_id?.message}
              {...register('sede_id', { setValueAs: comoNumero })}
            >
              <option value="">Elija una sede</option>
              {sedesActivas.map((sede) => (
                <option key={sede.id} value={sede.id}>
                  {sede.nombre}
                </option>
              ))}
            </Select>
          ) : (
            <p style={{ margin: 0 }}>Se carga en su sede ({sedePropia?.nombre}).</p>
          )}
          <Textarea
            etiqueta="Observaciones"
            rows={2}
            error={errors.observaciones?.message}
            {...register('observaciones')}
          />
        </div>
      </Card>
      <div className={estilos.barraDeAcciones}>
        <Button type="submit" cargando={crear.isPending}>
          Cargar ejemplar
        </Button>
        <Button variante="secondary" to="/ejemplares">
          Cancelar
        </Button>
      </div>
    </form>
  );
}
