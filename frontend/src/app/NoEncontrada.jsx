import { Button, EmptyState } from '../components/index.js';
import { useTituloDePagina } from '../hooks/useTituloDePagina.js';

export default function NoEncontrada() {
  useTituloDePagina('Pantalla no encontrada');
  return (
    <EmptyState
      titulo="La pantalla que busca no existe"
      descripcion="Revise la dirección o vuelva al inicio."
    >
      <Button to="/">Ir al inicio</Button>
    </EmptyState>
  );
}
