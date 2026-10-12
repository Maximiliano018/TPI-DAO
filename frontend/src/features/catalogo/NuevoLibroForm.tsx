import { useState, type FormEvent } from 'react'
import { useCategorias, useCrearLibro } from '../../api/consultas'
import { Button } from '../../components/Button/Button'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import styles from './formulario.module.css'

type Props = {
  alTerminar: (libroId?: number) => void
}

/** Alta de libro. Valida lo mínimo; las reglas (ISBN válido, sin duplicados) las valida el back. */
export function NuevoLibroForm({ alTerminar }: Props) {
  const categorias = useCategorias()
  const crear = useCrearLibro()
  const [datos, setDatos] = useState({
    isbn: '',
    titulo: '',
    autores: '',
    editorial: '',
    anio: '',
    categoria: '',
  })
  const cambiar = (campo: keyof typeof datos) => (valor: string) =>
    setDatos({ ...datos, [campo]: valor })

  function guardar(e: FormEvent) {
    e.preventDefault()
    crear.mutate(
      {
        isbn: datos.isbn,
        titulo: datos.titulo,
        // Varios autores separados por coma, en orden de autoría.
        autores: datos.autores.split(',').map((a) => a.trim()).filter(Boolean),
        editorial: datos.editorial.trim() || null,
        anio_publicacion: datos.anio ? Number(datos.anio) : null,
        categoria_id: datos.categoria ? Number(datos.categoria) : null,
      },
      { onSuccess: ({ id }) => alTerminar(id) },
    )
  }

  return (
    <form className={styles.formulario} onSubmit={guardar}>
      <Field etiqueta="ISBN *">
        <input
          className={claseControl}
          required
          placeholder="978-950-07-1234-5 (también ISBN-10)"
          value={datos.isbn}
          onChange={(e) => cambiar('isbn')(e.target.value)}
        />
      </Field>
      <Field etiqueta="Título *">
        <input
          className={claseControl}
          required
          value={datos.titulo}
          onChange={(e) => cambiar('titulo')(e.target.value)}
        />
      </Field>
      <Field etiqueta="Autores * (separados por coma)">
        <input
          className={claseControl}
          required
          placeholder="Jorge Luis Borges, Adolfo Bioy Casares"
          value={datos.autores}
          onChange={(e) => cambiar('autores')(e.target.value)}
        />
      </Field>
      <div className={styles.dosColumnas}>
        <Field etiqueta="Editorial">
          <input
            className={claseControl}
            value={datos.editorial}
            onChange={(e) => cambiar('editorial')(e.target.value)}
          />
        </Field>
        <Field etiqueta="Año">
          <input
            className={claseControl}
            type="number"
            min={1}
            value={datos.anio}
            onChange={(e) => cambiar('anio')(e.target.value)}
          />
        </Field>
      </div>
      <Field etiqueta="Categoría">
        <select
          className={claseControl}
          value={datos.categoria}
          onChange={(e) => cambiar('categoria')(e.target.value)}
        >
          <option value="">Sin categoría</option>
          {categorias.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
      </Field>

      {crear.isError && <p className={styles.error}>{crear.error.message}</p>}

      <div className={styles.botones}>
        <Button variante="ghost" onClick={() => alTerminar()}>
          Cancelar
        </Button>
        <Button type="submit" disabled={crear.isPending}>
          {crear.isPending ? 'Guardando…' : 'Guardar libro'}
        </Button>
      </div>
    </form>
  )
}
