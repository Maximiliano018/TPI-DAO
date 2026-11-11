import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import {
  ADMIN,
  BIBLIOTECARIO,
  SOCIO,
  evento,
  excepcion,
  pagina,
  sedeAdmin,
  sedeBasica,
  sedePublica,
} from '../../../../tests/datos.js';
import { error, registrar, responder, sesionDe } from '../../../../tests/handlers.js';
import { renderizarApp } from '../../../../tests/render.jsx';

const hoy = () => new Date().getDay() || 7;

describe('Detalle de sede', () => {
  it('administrador: datos, auditoría y pestañas, con acciones de una sede activa', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin());
    const { container } = renderizarApp('/sedes/1', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Sede Central' })).toBeVisible();
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual([
      'Datos',
      'Horarios',
      'Historial',
    ]);
    expect(screen.getByText('Av. Colón 1250')).toBeInTheDocument();
    expect(screen.getByText('Laura Pérez')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Auditoría' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Editar Sede Central' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Dar de baja Sede Central' })).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('sede en baja: muestra el bloque de baja y solo permite reactivar', async () => {
    sesionDe(ADMIN);
    responder(
      'get',
      '/sedes/1',
      sedeAdmin({
        estado: 'BAJA',
        baja: {
          fecha: '2026-10-20T12:00:00Z',
          motivo: 'Cierre del edificio',
          usuario: { id: 1, nombre: 'Ana Admin' },
        },
      }),
    );
    renderizarApp('/sedes/1', { conSesion: true });

    const bloque = await screen.findByRole('region', { name: 'Baja de la sede' });
    expect(within(bloque).getByText('Cierre del edificio')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reactivar Sede Central' })).toBeVisible();
    expect(screen.queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Abierta')).not.toBeInTheDocument();
  });

  it('horarios: resalta hoy y lista los cierres vigentes', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin({ excepciones: [excepcion()] }));
    const user = userEvent.setup();
    renderizarApp('/sedes/1?tab=horarios', { conSesion: true });

    const semana = await screen.findByRole('list', { name: 'Horario semanal' });
    const actual = within(semana).getAllByRole('listitem')[hoy() - 1];
    expect(actual).toHaveAttribute('aria-current', 'date');
    expect(actual).toHaveTextContent('(hoy)');
    const cierres = screen.getByRole('list', { name: 'Cierres vigentes' });
    expect(cierres).toHaveTextContent('24/12/2026');
    expect(cierres).toHaveTextContent('Cierre total');
    expect(cierres).toHaveTextContent('Víspera de Navidad');

    await user.click(screen.getByRole('tab', { name: 'Datos' }));
    expect(screen.getByText('Av. Colón 1250')).toBeInTheDocument();
  });

  it('agregar un cierre parcial envía el cuerpo esperado', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin());
    const alta = registrar('post', '/sedes/1/excepciones-horario', [excepcion()], 201);
    const user = userEvent.setup();
    renderizarApp('/sedes/1?tab=horarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Agregar cierre' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Agregar cierre' });
    // Sin datos, la validación impide enviar.
    await user.click(within(dialogo).getByRole('button', { name: 'Agregar cierre' }));
    expect(await within(dialogo).findByText('Ingrese la fecha')).toBeInTheDocument();
    expect(alta).toHaveLength(0);

    fireEvent.change(within(dialogo).getByLabelText(/Fecha \(o primer día\)/), {
      target: { value: '2026-12-24' },
    });
    await user.selectOptions(within(dialogo).getByLabelText(/Tipo de cierre/), 'CIERRE_PARCIAL');
    fireEvent.change(within(dialogo).getByLabelText(/Cerrada desde/), {
      target: { value: '10:00' },
    });
    fireEvent.change(within(dialogo).getByLabelText(/Cerrada hasta/), {
      target: { value: '12:00' },
    });
    await user.type(within(dialogo).getByLabelText(/Motivo/), 'Reunión');
    await user.click(within(dialogo).getByRole('button', { name: 'Agregar cierre' }));

    await waitFor(() => expect(alta).toHaveLength(1));
    expect(alta[0].cuerpo).toEqual({
      fecha_desde: '2026-12-24',
      fecha_hasta: null,
      tipo: 'CIERRE_PARCIAL',
      hora_desde: '10:00',
      hora_hasta: '12:00',
      motivo: 'Reunión',
    });
    expect(await screen.findByText('Cierre agregado')).toBeInTheDocument();
  });

  it('agregar un cierre: valida el rango y muestra el error del servidor', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin());
    registrar('post', '/sedes/1/excepciones-horario', () =>
      error(409, 'EXCEPCION_HORARIO_SUPERPUESTA', 'Superpuesta'),
    );
    const user = userEvent.setup();
    renderizarApp('/sedes/1?tab=horarios', { conSesion: true });

    await user.click(await screen.findByRole('button', { name: 'Agregar cierre' }));
    const dialogo = await screen.findByRole('dialog');
    fireEvent.change(within(dialogo).getByLabelText(/Fecha \(o primer día\)/), {
      target: { value: '2026-12-01' },
    });
    fireEvent.change(within(dialogo).getByLabelText(/Último día/), {
      target: { value: '2027-02-01' },
    });
    await user.click(within(dialogo).getByRole('button', { name: 'Agregar cierre' }));
    expect(await within(dialogo).findByText('El rango admite hasta 31 días')).toBeInTheDocument();

    fireEvent.change(within(dialogo).getByLabelText(/Último día/), { target: { value: '' } });
    await user.click(within(dialogo).getByRole('button', { name: 'Agregar cierre' }));
    expect(
      await within(dialogo).findByText('Ya hay un cierre cargado para esa fecha y horario'),
    ).toBeInTheDocument();
  });

  it('quitar un cierre pide confirmación', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin({ excepciones: [excepcion()] }));
    const baja = registrar('delete', '/sedes/1/excepciones-horario/7', null, 204);
    const user = userEvent.setup();
    renderizarApp('/sedes/1?tab=horarios', { conSesion: true });

    await user.click(
      await screen.findByRole('button', { name: 'Quitar el cierre del 24/12/2026' }),
    );
    const dialogo = await screen.findByRole('dialog', { name: 'Quitar cierre' });
    await user.click(within(dialogo).getByRole('button', { name: 'Quitar cierre' }));
    await waitFor(() => expect(baja).toHaveLength(1));
    expect(await screen.findByText('Cierre quitado')).toBeInTheDocument();
  });

  it('bibliotecario no puede agregar ni quitar cierres', async () => {
    sesionDe(BIBLIOTECARIO);
    responder('get', '/sedes/1', sedeBasica({ excepciones: [excepcion()] }));
    renderizarApp('/sedes/1?tab=horarios', { conSesion: true });

    await screen.findByRole('list', { name: 'Cierres vigentes' });
    expect(screen.queryByRole('button', { name: /Agregar cierre|Quitar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Historial' })).not.toBeInTheDocument();
  });

  it('socio: sin responsable ni historial', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes/1', sedePublica());
    renderizarApp('/sedes/1', { conSesion: true });

    expect(await screen.findByRole('heading', { level: 1, name: 'Sede Central' })).toBeVisible();
    expect(screen.queryByText('Responsable')).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Historial' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /baja|Reactivar/i })).not.toBeInTheDocument();
  });

  it('socio ante una sede en baja ve que no existe o no está disponible', async () => {
    sesionDe(SOCIO);
    responder('get', '/sedes/3', () => error(404, 'SEDE_NO_ENCONTRADA', 'No existe'));
    renderizarApp('/sedes/3', { conSesion: true });

    expect(
      await screen.findByText('La sede solicitada no existe o no está disponible'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver a sedes' })).toHaveAttribute('href', '/sedes');
  });

  it('historial: línea de tiempo con cambios, filtro por tipo y paginación', async () => {
    sesionDe(ADMIN);
    responder('get', '/sedes/1', sedeAdmin());
    const historial = registrar(
      'get',
      '/sedes/1/historial',
      pagina(
        [
          evento(),
          evento({
            id: 2,
            tipo_evento: 'BAJA',
            motivo: 'Cierre del edificio',
            estado_anterior: 'ACTIVA',
            estado_nuevo: 'BAJA',
            cambios: [],
          }),
        ],
        { total: 12, size: 10 },
      ),
    );
    const user = userEvent.setup();
    renderizarApp('/sedes/1?tab=historial', { conSesion: true });

    const linea = await screen.findByRole('list', { name: 'Historial de la sede' });
    const [modificacion, baja] = [...linea.children];
    expect(modificacion).toHaveTextContent('Modificación');
    expect(modificacion).toHaveTextContent('Ana Admin');
    expect(modificacion).toHaveTextContent('Teléfono: +543514221234 → +543514229999');
    expect(baja).toHaveTextContent('Estado: Activa → Baja');
    expect(baja).toHaveTextContent('Motivo: Cierre del edificio');

    await user.selectOptions(screen.getByLabelText('Tipo de evento'), 'BAJA');
    await waitFor(() => expect(historial.at(-1).url.searchParams.get('tipo_evento')).toBe('BAJA'));
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    await waitFor(() => expect(historial.at(-1).url.searchParams.get('page')).toBe('2'));
  });

  describe('baja y reactivación', () => {
    it('baja bloqueada: lista los impedimentos por tipo y no ofrece forzar', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes/1', sedeAdmin());
      responder(
        'post',
        '/sedes/1/baja',
        () =>
          error(
            409,
            'SEDE_CON_ACTIVIDAD_PENDIENTE',
            'La sede tiene actividad pendiente: 12 bibliotecarios asignados.',
            [
              {
                tipo: 'BIBLIOTECARIOS_ASIGNADOS',
                cantidad: 12,
                hay_mas: true,
                elementos: Array.from({ length: 10 }, (_, i) => ({
                  id: i + 1,
                  referencia: `bibl${i + 1}`,
                  estado: 'ACTIVO',
                })),
              },
            ],
          ),
        409,
      );
      const user = userEvent.setup();
      renderizarApp('/sedes/1', { conSesion: true });

      await user.click(await screen.findByRole('button', { name: 'Dar de baja Sede Central' }));
      const confirmacion = await screen.findByRole('dialog', { name: 'Dar de baja Sede Central' });
      await user.type(within(confirmacion).getByLabelText(/Motivo de la baja/), 'Reforma total');
      await user.click(within(confirmacion).getByRole('button', { name: 'Dar de baja' }));

      const bloqueo = await screen.findByRole('dialog', {
        name: 'No se puede dar de baja la sede',
      });
      expect(bloqueo).toHaveTextContent('Bibliotecarios asignados (12)');
      expect(bloqueo).toHaveTextContent('bibl1, bibl2');
      expect(bloqueo).toHaveTextContent('y 2 más');
      expect(within(bloqueo).getByRole('link', { name: /Ver bibliotecarios/ })).toHaveAttribute(
        'href',
        '/usuarios?sede_id=1&estado=activos',
      );
      expect(within(bloqueo).getAllByRole('button')).toHaveLength(1);
      await user.click(within(bloqueo).getByRole('button', { name: 'Entendido' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('conflicto de versión en la baja: pide recargar', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes/1', sedeAdmin());
      responder('post', '/sedes/1/baja', () => error(409, 'CONFLICTO_DE_VERSION', 'Cambió'), 409);
      const user = userEvent.setup();
      renderizarApp('/sedes/1', { conSesion: true });

      await user.click(await screen.findByRole('button', { name: 'Dar de baja Sede Central' }));
      const dialogo = await screen.findByRole('dialog');
      await user.type(within(dialogo).getByLabelText(/Motivo de la baja/), 'Motivo válido');
      await user.click(within(dialogo).getByRole('button', { name: 'Dar de baja' }));
      expect(
        await screen.findByRole('dialog', { name: 'Otra persona modificó esta sede' }),
      ).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Recargar' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('reactivar confirma el efecto y envía la versión', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes/1', sedeAdmin({ estado: 'BAJA', version: 6 }));
      const reactivar = registrar('post', '/sedes/1/reactivar', sedeAdmin());
      const user = userEvent.setup();
      renderizarApp('/sedes/1', { conSesion: true });

      await user.click(await screen.findByRole('button', { name: 'Reactivar Sede Central' }));
      const dialogo = await screen.findByRole('dialog', { name: 'Reactivar Sede Central' });
      expect(dialogo).toHaveTextContent('Se conserva su historial');
      await user.click(within(dialogo).getByRole('button', { name: 'Reactivar' }));
      await waitFor(() => expect(reactivar).toHaveLength(1));
      expect(reactivar[0].cuerpo).toEqual({ version: 6 });
      expect(await screen.findByText('Sede reactivada')).toBeInTheDocument();
    });

    it('un error al reactivar se muestra dentro del diálogo', async () => {
      sesionDe(ADMIN);
      responder('get', '/sedes/1', sedeAdmin({ estado: 'BAJA' }));
      responder('post', '/sedes/1/reactivar', () => error(409, 'SEDE_YA_ACTIVA', 'Ya activa'), 409);
      const user = userEvent.setup();
      renderizarApp('/sedes/1', { conSesion: true });

      await user.click(await screen.findByRole('button', { name: 'Reactivar Sede Central' }));
      const dialogo = await screen.findByRole('dialog');
      await user.click(within(dialogo).getByRole('button', { name: 'Reactivar' }));
      expect(
        await within(dialogo).findByText(
          'La sede ya estaba en ese estado. Se actualizó la pantalla',
        ),
      ).toBeInTheDocument();
    });
  });
});
