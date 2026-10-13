import { useState, type FormEvent } from 'react'
import { useActualizarSede, useCrearSede } from '../../api/consultas'
import type { Sede } from '../../api/tipos'
import { Button } from '../../components/Button/Button'
import { claseControl } from '../../components/Field/control'
import { Field } from '../../components/Field/Field'
import styles from '../comun/formulario.module.css'

type Props = {
  /** Sin sede: alta. Con sede: edición de sus datos (el código no se modifica). */
  sede?: Sede
  alTerminar: () => void
}

/** Alta y edición de sede. Las reglas (código válido, sin duplicados) las valida el back. */
export function SedeForm({ sede, alTerminar }: Props) {
  const crear = useCrearSede()
  const actualizar = useActualizarSede()
  const cambio = sede ? actualizar : crear
  const [datos, setDatos] = useState({
    codigo: sede?.codigo ?? '',
    nombre: sede?.nombre ?? '',
    direccion: sede?.direccion ?? '',
    localidad: sede?.localidad ?? '',
    telefono: sede?.telefono ?? '',
    email: sede?.email ?? '',
  })
  const cambiar = (campo: keyof typeof datos) => (valor: string) =>
    setDatos({ ...datos, [campo]: valor })

  function guardar(e: FormEvent) {
    e.preventDefault()
    const editables = {
      nombre: datos.nombre,
      direccion: datos.direccion,
      localidad: datos.localidad,
      telefono: datos.telefono.trim() || null,
      email: datos.email.trim() || null,
    }
    if (sede) actualizar.mutate({ id: sede.id, datos: editables }, { onSuccess: alTerminar })
    else crear.mutate({ codigo: datos.codigo, ...editables }, { onSuccess: alTerminar })
  }

  return (
    <form className={styles.formulario} onSubmit={guardar}>
      <div className={styles.dosColumnas}>
        <Field etiqueta="Nombre *">
          <input
            className={claseControl}
            required
            maxLength={100}
            value={datos.nombre}
            onChange={(e) => cambiar('nombre')(e.target.value)}
          />
        </Field>
        <Field etiqueta={sede ? 'Código' : 'Código *'}>
          <input
            className={claseControl}
            required
            disabled={Boolean(sede)}
            minLength={2}
            maxLength={5}
            placeholder="CEN"
            title="Entre 2 y 5 letras. No se puede cambiar después: forma parte de los códigos de inventario."
            value={datos.codigo}
            onChange={(e) => cambiar('codigo')(e.target.value.toUpperCase())}
          />
        </Field>
      </div>
      <Field etiqueta="Dirección *">
        <input
          className={claseControl}
          required
          maxLength={200}
          value={datos.direccion}
          onChange={(e) => cambiar('direccion')(e.target.value)}
        />
      </Field>
      <Field etiqueta="Localidad *">
        <input
          className={claseControl}
          required
          maxLength={100}
          value={datos.localidad}
          onChange={(e) => cambiar('localidad')(e.target.value)}
        />
      </Field>
      <div className={styles.dosColumnas}>
        <Field etiqueta="Email">
          <input
            className={claseControl}
            type="email"
            maxLength={120}
            value={datos.email}
            onChange={(e) => cambiar('email')(e.target.value)}
          />
        </Field>
        <Field etiqueta="Teléfono">
          <input
            className={claseControl}
            maxLength={30}
            value={datos.telefono}
            onChange={(e) => cambiar('telefono')(e.target.value)}
          />
        </Field>
      </div>

      {cambio.isError && <p className={styles.error}>{cambio.error.message}</p>}

      <div className={styles.botones}>
        <Button variante="ghost" onClick={alTerminar}>
          Cancelar
        </Button>
        <Button type="submit" disabled={cambio.isPending}>
          {cambio.isPending ? 'Guardando…' : sede ? 'Guardar cambios' : 'Crear sede'}
        </Button>
      </div>
    </form>
  )
}
