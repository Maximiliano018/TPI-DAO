import { useEffect, useRef, type ReactNode } from 'react'
import styles from './Modal.module.css'

type Props = {
  abierto: boolean
  titulo: string
  alCerrar: () => void
  children: ReactNode
}

/** Ventana emergente. Usa <dialog>: el navegador maneja el foco y cierra con Escape. */
export function Modal({ abierto, titulo, alCerrar, children }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const d = dialogo.current
    if (!d) return
    if (abierto && !d.open) d.showModal()
    if (!abierto && d.open) d.close()
  }, [abierto])

  return (
    <dialog ref={dialogo} className={styles.modal} onClose={alCerrar}>
      <h2 className={styles.titulo}>{titulo}</h2>
      {abierto && children}
    </dialog>
  )
}
