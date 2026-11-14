import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
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
import { TIPOS_DE_MATERIAL } from '../../../utils/estados.js';
import estilos from '../../sedes/components/Sedes.module.css';
import { esquemaLibro } from '../esquema.js';
import { useCategorias, useCrearLibro, useLibro, useModificarLibro } from '../hooks/useCatalogo.js';

const CAMPOS = ['isbn', 'titulo', 'autores', 'editorial', 'anio_edicion', 'categoria_id'];
const comoNumero = (valor) => (valor === '' ? undefined : Number(valor));

function Formulario({ libro, categorias }) {
  const editando = Boolean(libro);
  const navegar = useNavigate();
  const { mostrar } = useToast();
  const crear = useCrearLibro();
  const modificar = useModificarLibro(libro?.id);
  const mutacion = editando ? modificar : crear;
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [existente, setExistente] = useState(null);
  const {
    register,
    handleSubmit,
    setError,
    setFocus,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esquemaLibro),
    defaultValues: {
      isbn: libro?.isbn ?? '',
      titulo: libro?.titulo ?? '',
      autores: (libro?.autores ?? []).join('\n'),
      editorial: libro?.editorial ?? '',
      anio_edicion: libro?.anio_edicion ?? '',
      categoria_id: libro?.categoria.id,
      tipo_material: libro?.tipo_material ?? 'LIBRO',
    },
  });

  function enviar(datos) {
    setErrorGeneral(null);
    setExistente(null);
    const cuerpo = {
      isbn: datos.isbn || null,
      titulo: datos.titulo,
      autores: datos.autores
        .split('\n')
        .map((a) => a.trim())
        .filter(Boolean),
      editorial: datos.editorial || null,
      anio_edicion: datos.anio_edicion === '' ? null : datos.anio_edicion,
      categoria_id: datos.categoria_id,
      tipo_material: datos.tipo_material,
      // La versión evita pisar los cambios de otra persona (CONFLICTO_DE_VERSION).
      ...(editando ? { version: libro.version } : {}),
    };
    mutacion.mutate(cuerpo, {
      onSuccess: (guardado) => {
        mostrar(editando ? 'Libro guardado' : 'Libro creado');
        navegar(`/catalogo/${guardado.id}`);
      },
      onError: (error) => {
        if (error.codigo === 'LIBRO_DUPLICADO') {
          setExistente(error.detalles[0]?.libro_id ?? null);
          setErrorGeneral(error.mensaje);
          return;
        }
        const porCampo = erroresPorCampo(error);
        const campos = CAMPOS.filter((c) => porCampo[c]);
        for (const c of campos) setError(c, { message: porCampo[c] });
        if (campos.length > 0) setFocus(campos[0]);
        else setErrorGeneral(mensajeDeError(error));
      },
    });
  }

  return (
    <form className={estilos.formulario} noValidate onSubmit={handleSubmit(enviar)}>
      {errorGeneral && (
        <Alert tono="danger">
          {errorGeneral}{' '}
          {existente && <Link to={`/catalogo/${existente}`}>Ver el libro existente</Link>}
        </Alert>
      )}
      <Card titulo="Obra">
        <div className={estilos.grupo}>
          <Input
            etiqueta="Título"
            requerido
            autoComplete="off"
            error={errors.titulo?.message}
            {...register('titulo')}
          />
          <Textarea
            etiqueta="Autores"
            requerido
            rows={3}
            ayuda="Uno por línea, en el orden en que figuran en la obra."
            error={errors.autores?.message}
            {...register('autores')}
          />
          <Input
            etiqueta="ISBN"
            autoComplete="off"
            ayuda="10 o 13 dígitos, con o sin guiones. Sin ISBN, se controla por título, autor, editorial y año."
            error={errors.isbn?.message}
            {...register('isbn')}
          />
        </div>
      </Card>
      <Card titulo="Edición y clasificación">
        <div className={estilos.grupo}>
          <Input
            etiqueta="Editorial"
            autoComplete="off"
            error={errors.editorial?.message}
            {...register('editorial')}
          />
          <Input
            etiqueta="Año de edición"
            inputMode="numeric"
            autoComplete="off"
            error={errors.anio_edicion?.message}
            {...register('anio_edicion')}
          />
          <Select
            etiqueta="Categoría"
            requerido
            error={errors.categoria_id?.message}
            {...register('categoria_id', { setValueAs: comoNumero })}
          >
            <option value="">Elija una categoría</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </Select>
          <Select etiqueta="Tipo de material" requerido {...register('tipo_material')}>
            {Object.entries(TIPOS_DE_MATERIAL).map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </Select>
        </div>
      </Card>
      <div className={estilos.barraDeAcciones}>
        <Button type="submit" cargando={mutacion.isPending}>
          {editando ? 'Guardar cambios' : 'Crear libro'}
        </Button>
        <Button variante="secondary" to={editando ? `/catalogo/${libro.id}` : '/catalogo'}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

/** Alta (`/catalogo/nuevo`) y edición (`/catalogo/:id/editar`) de un libro (administrador). */
export default function LibroFormPage({ modo }) {
  const { id } = useParams();
  const editando = modo === 'editar';
  const titulo = editando ? 'Editar libro' : 'Nuevo libro';
  useTituloDePagina(titulo);
  const libro = useLibro(id, { enabled: editando });
  const categorias = useCategorias();
  const migas = [{ texto: 'Catálogo', to: '/catalogo' }, { texto: titulo }];

  const cargando = categorias.isPending || (editando && libro.isPending);
  const error = categorias.error ?? (editando ? libro.error : null);
  return (
    <>
      <PageHeader
        titulo={titulo}
        descripcion={
          editando
            ? libro.data?.titulo
            : 'El libro es la obra; las copias físicas son los ejemplares de cada sede.'
        }
        migas={<Breadcrumb items={migas} />}
      />
      {cargando && <Skeleton alto={240} />}
      {!cargando && error && <ErrorState error={error} />}
      {!cargando && !error && (
        <Formulario libro={editando ? libro.data : undefined} categorias={categorias.data} />
      )}
    </>
  );
}
