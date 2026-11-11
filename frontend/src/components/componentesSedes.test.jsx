import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { agruparHorarios, validarHorarios } from '../features/sedes/horarios.js';
import { BusquedaConEspera, Combobox, Timeline, WeekScheduleEditor } from './index.js';

const OPCIONES = [
  { id: 1, texto: 'Córdoba', detalle: 'Capital' },
  { id: 2, texto: 'Villa María' },
  { id: 3, texto: 'Río Cuarto' },
];

function ComboboxControlado() {
  const [valor, setValor] = useState('');
  return (
    <>
      <Combobox etiqueta="Localidad" opciones={OPCIONES} valor={valor} onCambiar={setValor} />
      <output data-testid="valor">{String(valor)}</output>
    </>
  );
}

describe('Combobox', () => {
  it('filtra sin distinguir tildes ni mayúsculas y elige con el teclado', async () => {
    const user = userEvent.setup();
    const { container } = render(<ComboboxControlado />);
    const campo = screen.getByRole('combobox', { name: 'Localidad' });
    await user.click(campo);
    await user.type(campo, 'rio');
    expect(screen.getAllByRole('option')).toHaveLength(1);
    await user.keyboard('{Enter}');
    expect(screen.getByTestId('valor')).toHaveTextContent('3');
    expect(campo).toHaveValue('Río Cuarto');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('navega con flechas, cierra con Escape y avisa si no hay coincidencias', async () => {
    const user = userEvent.setup();
    render(<ComboboxControlado />);
    const campo = screen.getByRole('combobox', { name: 'Localidad' });
    await user.click(campo);
    await user.keyboard('{ArrowDown}{Enter}');
    expect(screen.getByTestId('valor')).toHaveTextContent('2');
    await user.clear(campo);
    await user.type(campo, 'zzz');
    expect(screen.getByText('Sin coincidencias')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(campo).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('BusquedaConEspera', () => {
  it('informa el texto recién después de la espera', async () => {
    const onBuscar = vi.fn();
    const user = userEvent.setup();
    render(<BusquedaConEspera etiqueta="Buscar" valor="" onBuscar={onBuscar} esperaMs={50} />);
    await user.type(screen.getByRole('searchbox', { name: 'Buscar' }), 'cen');
    expect(onBuscar).not.toHaveBeenCalled();
    await vi.waitFor(() => expect(onBuscar).toHaveBeenCalledWith('cen'));
    expect(onBuscar).toHaveBeenCalledTimes(1);
  });
});

describe('Timeline', () => {
  it('muestra los eventos como lista ordenada accesible', async () => {
    const { container } = render(
      <Timeline
        etiqueta="Historial"
        items={[
          { id: 1, titulo: 'Alta', meta: 'Ana · 14/10/2026', contenido: <p>Detalle</p> },
          { id: 2, titulo: 'Baja' },
        ]}
      />,
    );
    expect(screen.getByRole('list', { name: 'Historial' })).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(await axe(container)).toHaveNoViolations();
  });
});

function EditorControlado({ inicial = agruparHorarios([]) }) {
  const [valor, setValor] = useState(inicial);
  const problemas = validarHorarios(valor);
  delete problemas.general;
  return <WeekScheduleEditor valor={valor} onCambiar={setValor} problemas={problemas} />;
}

describe('WeekScheduleEditor', () => {
  it('agrega, quita y marca como cerrado', async () => {
    const user = userEvent.setup();
    const { container } = render(<EditorControlado />);
    await user.click(screen.getByRole('button', { name: 'Agregar franja el Lunes' }));
    expect(screen.getByLabelText('Lunes, franja 1: apertura')).toHaveValue('09:00');
    await user.click(screen.getByRole('button', { name: 'Agregar franja el Lunes' }));
    expect(screen.getByLabelText('Lunes, franja 2: apertura')).toHaveValue('13:00');
    await user.click(screen.getByRole('button', { name: 'Quitar Lunes, franja 2' }));
    expect(screen.queryByLabelText('Lunes, franja 2: apertura')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Marcar Lunes como cerrado' }));
    expect(screen.queryByLabelText('Lunes, franja 1: apertura')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('marca el cierre anterior a la apertura mientras se escribe', () => {
    render(
      <EditorControlado
        inicial={agruparHorarios([{ dia_semana: 1, apertura: '09:00', cierre: '13:00' }])}
      />,
    );
    fireEvent.change(screen.getByLabelText('Lunes, franja 1: cierre'), {
      target: { value: '08:00' },
    });
    expect(screen.getByText(/el cierre debe ser posterior a la apertura/)).toBeInTheDocument();
    expect(screen.getByLabelText('Lunes, franja 1: cierre')).toBeInvalid();
  });

  it('copia el horario de un día a otros', async () => {
    const user = userEvent.setup();
    render(
      <EditorControlado
        inicial={agruparHorarios([{ dia_semana: 1, apertura: '09:00', cierre: '13:00' }])}
      />,
    );
    await user.click(
      screen.getByRole('button', { name: 'Copiar el horario del Lunes a otros días' }),
    );
    await user.click(screen.getByRole('checkbox', { name: 'Martes' }));
    await user.click(screen.getByRole('checkbox', { name: 'Miércoles' }));
    await user.click(screen.getByRole('button', { name: 'Copiar' }));
    expect(screen.getByLabelText('Martes, franja 1: apertura')).toHaveValue('09:00');
    expect(screen.getByLabelText('Miércoles, franja 1: cierre')).toHaveValue('13:00');
    expect(screen.queryByLabelText('Jueves, franja 1: apertura')).not.toBeInTheDocument();
  });
});
