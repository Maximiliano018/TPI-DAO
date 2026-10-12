import type { ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: 'primary' | 'secondary' | 'ghost' | 'peligro'
  tamano?: 'normal' | 'chico'
}

export function Button({
  variante = 'primary',
  tamano = 'normal',
  type = 'button',
  className,
  ...props
}: Props) {
  const clases = [styles.boton, styles[variante], tamano === 'chico' && styles.chico, className]
  return <button type={type} className={clases.filter(Boolean).join(' ')} {...props} />
}
