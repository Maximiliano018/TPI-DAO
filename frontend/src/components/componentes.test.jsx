import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Checkbox,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Input,
  Modal,
  PageHeader,
  Pagination,
  Select,
  Skeleton,
  Spinner,
  StatCard,
  Table,
  Tabs,
  Textarea,
  ToastProvider,
  useToast,
} from './index.js';
import { useState } from 'react';

const envolver = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('Button', () => {
  it('cargando se deshabilita y se anuncia como ocupado', () => {
    envolver(<Button cargando>Guardar</Button>);
    const boton = screen.getByRole('button', { name: 'Guardar' });
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute('aria-busy', 'true');
  });

  it('con `to` es un enlace', () => {
    envolver(<Button to="/sedes">Sedes</Button>);
    expect(screen.getByRole('link', { name: 'Sedes' })).toHaveAttribute('href', '/sedes');
  });
});

describe('campos de formulario', () => {
  it('asocian etiqueta, ayuda y error por aria-describedby', () => {
    const { container } = render(
      <>
        <Input
          etiqueta="Nombre"
          ayuda="Como figura en el documento"
          error="Es obligatorio"
          requerido
        />
        <Select etiqueta="Rol">
          <option>Uno</option>
        </Select>
        <Textarea etiqueta="Motivo" />
        <Checkbox etiqueta="Confirmo" />
      </>,
    );
    const campo = screen.getByLabelText(/Nombre/);
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(campo).toHaveAccessibleDescription('Como figura en el documento Es obligatorio');
    expect(screen.getByRole('alert')).toHaveTextContent('Es obligatorio');
    return axe(container).then((r) => expect(r).toHaveNoViolations());
  });
});

describe('Modal', () => {
  function Ejemplo({ onCerrar, bloqueado }) {
    return (
      <>
        <button>Afuera</button>
        <Modal
          titulo="Título"
          onCerrar={onCerrar}
          bloqueado={bloqueado}
          acciones={<button>Aceptar</button>}
        >
          <input aria-label="Dato" />
        </Modal>
      </>
    );
  }

  it('enfoca el primer control, atrapa el foco y Escape cierra', async () => {
    const onCerrar = vi.fn();
    const user = userEvent.setup();
    render(<Ejemplo onCerrar={onCerrar} />);

    expect(screen.getByRole('dialog', { name: 'Título' })).toBeInTheDocument();
    expect(screen.getByLabelText('Dato')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Aceptar' })).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText('Dato')).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Aceptar' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(onCerrar).toHaveBeenCalledOnce();
  });

  it('mientras se procesa, Escape no cierra', async () => {
    const onCerrar = vi.fn();
    render(<Ejemplo onCerrar={onCerrar} bloqueado />);

    await userEvent.setup().keyboard('{Escape}');

    expect(onCerrar).not.toHaveBeenCalled();
  });

  it('devuelve el foco a quien lo abrió', async () => {
    function Abre() {
      const [abierto, setAbierto] = useState(false);
      return (
        <>
          <button onClick={() => setAbierto(true)}>Abrir</button>
          {abierto && (
            <Modal titulo="Hola" onCerrar={() => setAbierto(false)}>
              <button>Cerrar</button>
            </Modal>
          )}
        </>
      );
    }
    const user = userEvent.setup();
    render(<Abre />);

    await user.click(screen.getByRole('button', { name: 'Abrir' }));
    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.getByRole('button', { name: 'Abrir' })).toHaveFocus());
  });

  it('no tiene violaciones de accesibilidad', async () => {
    render(<Ejemplo onCerrar={() => {}} />);
    expect(await axe(document.body)).toHaveNoViolations();
  });
});

describe('ConfirmDialog', () => {
  it('describe el efecto, confirma y deshabilita mientras procesa', async () => {
    const onConfirmar = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <ConfirmDialog
        titulo="Reactivar sede"
        descripcion="La sede volverá a operar."
        textoConfirmar="Reactivar"
        onConfirmar={onConfirmar}
        onCancelar={() => {}}
      />,
    );

    expect(screen.getByText('La sede volverá a operar.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Reactivar' }));
    expect(onConfirmar).toHaveBeenCalledOnce();

    rerender(
      <ConfirmDialog
        titulo="Reactivar sede"
        textoConfirmar="Reactivar"
        procesando
        onConfirmar={onConfirmar}
        onCancelar={() => {}}
      />,
    );
    expect(screen.getByRole('button', { name: 'Reactivar' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
  });
});

describe('Table y Pagination', () => {
  const columnas = [
    { clave: 'nombre', titulo: 'Nombre', orden: 'nombre' },
    { clave: 'codigo', titulo: 'Código' },
  ];
  const filas = [
    { id: 1, nombre: 'Alfa', codigo: 'AAA' },
    { id: 2, nombre: 'Beta', codigo: 'BBB' },
  ];

  it('muestra las filas, marca el orden y pide el orden contrario al repetir', async () => {
    const onOrden = vi.fn();
    const user = userEvent.setup();
    const { container } = envolver(
      <Table
        etiqueta="Sedes"
        columnas={columnas}
        filas={filas}
        idDe={(f) => f.id}
        orden="nombre"
        onOrden={onOrden}
      />,
    );

    expect(screen.getByRole('table', { name: 'Sedes' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Nombre/ })).toHaveAttribute(
      'aria-sort',
      'ascending',
    );
    await user.click(screen.getByRole('button', { name: /Nombre/ }));
    expect(onOrden).toHaveBeenCalledWith('-nombre');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('pagina con anterior, siguiente y tamaño', async () => {
    const onPage = vi.fn();
    const onSize = vi.fn();
    const user = userEvent.setup();
    envolver(<Pagination page={2} size={10} total={35} onPage={onPage} onSize={onSize} />);

    expect(screen.getByText('11–20 de 35')).toBeInTheDocument();
    expect(screen.getByText('Página 2 de 4')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    await user.click(screen.getByRole('button', { name: 'Anterior' }));
    await user.selectOptions(screen.getByLabelText('Por página'), '50');
    expect(onPage.mock.calls).toEqual([[3], [1]]);
    expect(onSize).toHaveBeenCalledWith(50);
  });

  it('en los extremos deshabilita anterior o siguiente y sin datos lo dice', () => {
    const { rerender } = envolver(<Pagination page={1} size={10} total={5} onPage={() => {}} />);
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
    rerender(
      <MemoryRouter>
        <Pagination page={1} size={10} total={0} onPage={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Sin resultados')).toBeInTheDocument();
  });
});

describe('Tabs', () => {
  it('cambia de pestaña con flechas, Inicio y Fin', async () => {
    function Ejemplo() {
      const [activa, setActiva] = useState('a');
      return (
        <Tabs
          activa={activa}
          onCambiar={setActiva}
          tabs={[
            { id: 'a', titulo: 'Datos', contenido: <p>Panel A</p> },
            { id: 'b', titulo: 'Horarios', contenido: <p>Panel B</p> },
            { id: 'c', titulo: 'Historial', contenido: <p>Panel C</p> },
          ]}
        />
      );
    }
    const user = userEvent.setup();
    const { container } = render(<Ejemplo />);

    screen.getByRole('tab', { name: 'Datos' }).focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Horarios' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Panel B')).toBeVisible();
    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: 'Historial' })).toHaveFocus();
    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: 'Datos' })).toHaveAttribute('aria-selected', 'true');
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Toast', () => {
  it('muestra el aviso en una región aria-live y se puede cerrar', async () => {
    function Ejemplo() {
      const { mostrar } = useToast();
      return <button onClick={() => mostrar('Sede guardada')}>Guardar</button>;
    }
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Ejemplo />
      </ToastProvider>,
    );

    await user.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(screen.getByRole('status')).toHaveTextContent('Sede guardada');
    await user.click(screen.getByRole('button', { name: 'Cerrar aviso' }));
    expect(screen.queryByText('Sede guardada')).not.toBeInTheDocument();
  });
});

describe('presentación', () => {
  it('Alert usa role alert para errores y status para el resto; Badge lleva texto', () => {
    const { container } = envolver(
      <>
        <Alert tono="danger">Falló</Alert>
        <Alert tono="info">Aviso</Alert>
        <Badge tono="success">Activa</Badge>
        <Card titulo="Tarjeta">Contenido</Card>
        <Spinner />
        <Skeleton />
        <EmptyState titulo="Nada por acá" descripcion="Pruebe otro filtro" />
        <ErrorState error={{ codigo: 'X', mensaje: 'Se cayó' }} onReintentar={() => {}} />
        <StatCard etiqueta="Activas" valor={3} to="/sedes" />
        <Breadcrumb items={[{ texto: 'Sedes', to: '/sedes' }, { texto: 'Central' }]} />
        <PageHeader
          titulo="Pantalla"
          descripcion="Descripción"
          acciones={<Button>Acción</Button>}
        />
      </>,
    );

    expect(screen.getAllByRole('alert')[0]).toHaveTextContent('Falló');
    expect(screen.getByText('Aviso').closest('[role]')).toHaveAttribute('role', 'status');
    expect(screen.getByText('Central')).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
    return axe(container).then((r) => expect(r).toHaveNoViolations());
  });
});
