import { Link } from 'react-router-dom';
import { FiltroSelect, Pagination, Table } from '../../../components/index.js';
import {
  activosYEnTransito,
  disponibilidadPorSede,
  enviosEIncidencias,
  librosMasSolicitados,
  movimientoEntreSedes,
  vencidosYMultas,
} from '../../../api/reportes.js';
import { ESTADOS, MOTIVOS_DE_REMITO, TIPOS_DE_PRESTAMO, estadoDe } from '../../../utils/estados.js';
import { formatearFecha, formatearMonto } from '../../../utils/formato.js';
import { useCategorias } from '../../catalogo/hooks/useCatalogo.js';
import EstadoBadge from '../../prestamos/components/EstadoBadge.jsx';
import {
  BotonCsv,
  FiltroSede,
  FiltrosConPeriodo,
  Indicadores,
  Resultado,
  Seccion,
  useFiltrosDeReporte,
  useReporte,
} from './comunes.jsx';
import estilos from './Reportes.module.css';

const porcentaje = (tasa) => (tasa === null ? '—' : `${Math.round(tasa * 1000) / 10} %`);

/** Columnas compartidas por la tabla y el CSV: `valor` es el texto; `render`, lo que se ve. */
const aTabla = (columnas) =>
  columnas.map(({ clave, titulo, valor, render }) => ({ clave, titulo, render: render ?? valor }));

function FiltroCategoria({ valor, onCambiar }) {
  const categorias = useCategorias();
  return (
    <FiltroSelect etiqueta="Categoría" valor={valor ?? ''} onCambiar={onCambiar}>
      <option value="">Todas</option>
      {categorias.data?.map((c) => (
        <option key={c.id} value={c.id}>
          {c.nombre}
        </option>
      ))}
    </FiltroSelect>
  );
}

function Tabla({ etiqueta, nombre, columnas, filas, idDe }) {
  return (
    <Seccion
      titulo={etiqueta}
      acciones={<BotonCsv nombre={nombre} columnas={columnas} filas={filas} />}
    >
      <Table etiqueta={etiqueta} columnas={aTabla(columnas)} filas={filas} idDe={idDe} />
    </Seccion>
  );
}

// --- R1 --------------------------------------------------------------------------------------

const COLUMNAS_R1 = [
  { clave: 'origen', titulo: 'Origen', valor: (r) => r.sede_origen },
  { clave: 'destino', titulo: 'Destino', valor: (r) => r.sede_destino },
  { clave: 'envios', titulo: 'Envíos', valor: (r) => r.envios },
  { clave: 'ejemplares', titulo: 'Ejemplares', valor: (r) => r.ejemplares },
  {
    clave: 'transito',
    titulo: 'Tránsito promedio (días)',
    valor: (r) => r.tiempo_promedio_transito_dias.toLocaleString('es-AR'),
  },
];

export function MovimientoEntreSedes() {
  const control = useFiltrosDeReporte(['desde', 'hasta', 'sede_id']);
  const { filtros } = control;
  const consulta = useReporte(
    'r1',
    movimientoEntreSedes,
    { desde: filtros.desde, hasta: filtros.hasta, sede_id: filtros.sede_id },
    { habilitado: !control.rangoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Remitos que llegaron a destino en el período, por ruta. El tránsito va del despacho a la
        recepción; los envíos que siguen en camino no entran.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros del movimiento entre sedes" control={control}>
        <FiltroSede valor={filtros.sede_id} onCambiar={(sede_id) => control.cambiar({ sede_id })} />
      </FiltrosConPeriodo>
      <Resultado consulta={consulta} vacio={(d) => d.rutas.length === 0}>
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Envíos recibidos', valor: d.total_envios },
                { etiqueta: 'Ejemplares movidos', valor: d.total_ejemplares },
                { etiqueta: 'Rutas', valor: d.rutas.length },
              ]}
            />
            <Tabla
              etiqueta="Rutas entre sedes"
              nombre="movimiento-entre-sedes"
              columnas={COLUMNAS_R1}
              filas={d.rutas}
              idDe={(r) => `${r.sede_origen_id}-${r.sede_destino_id}`}
            />
          </>
        )}
      </Resultado>
    </div>
  );
}

// --- R2 --------------------------------------------------------------------------------------

const COLUMNAS_R2 = [
  { clave: 'sede', titulo: 'Sede origen', valor: (s) => s.sede },
  { clave: 'total', titulo: 'Envíos', valor: (s) => s.total_envios },
  { clave: 'recibidos', titulo: 'Recibidos', valor: (s) => s.recibidos },
  { clave: 'extraviados', titulo: 'Extraviados', valor: (s) => s.extraviados },
  { clave: 'danados', titulo: 'Dañados', valor: (s) => s.danados },
  { clave: 'destruidos', titulo: 'Destruidos', valor: (s) => s.destruidos },
  { clave: 'exito', titulo: 'Éxito', valor: (s) => porcentaje(s.tasa_exito) },
];

export function EnviosEIncidencias() {
  const control = useFiltrosDeReporte(['desde', 'hasta', 'sede_id']);
  const { filtros } = control;
  const consulta = useReporte(
    'r2',
    enviosEIncidencias,
    { desde: filtros.desde, hasta: filtros.hasta, sede_id: filtros.sede_id },
    { habilitado: !control.rangoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Remitos cerrados despachados en el período: cuántos llegaron bien y cuántos con incidencias.
        No cuenta los anulados ni los que siguen abiertos.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros de envíos e incidencias" control={control}>
        <FiltroSede valor={filtros.sede_id} onCambiar={(sede_id) => control.cambiar({ sede_id })} />
      </FiltrosConPeriodo>
      <Resultado consulta={consulta} vacio={(d) => d.total_envios === 0}>
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Envíos cerrados', valor: d.total_envios },
                { etiqueta: 'Tasa de éxito', valor: porcentaje(d.tasa_exito) },
                { etiqueta: 'Con incidencias', valor: porcentaje(d.tasa_incidencias) },
                { etiqueta: 'Extraviados', valor: d.extraviados },
              ]}
            />
            <Tabla
              etiqueta="Envíos por sede"
              nombre="envios-e-incidencias"
              columnas={COLUMNAS_R2}
              filas={d.por_sede}
              idDe={(s) => s.sede_id}
            />
          </>
        )}
      </Resultado>
    </div>
  );
}

// --- R3 --------------------------------------------------------------------------------------

const COLUMNAS_R3 = [
  { clave: 'posicion', titulo: '#', valor: (l) => l.posicion },
  {
    clave: 'titulo',
    titulo: 'Libro',
    valor: (l) => l.titulo,
    render: (l) => <Link to={`/catalogo/${l.libro_id}`}>{l.titulo}</Link>,
  },
  { clave: 'prestamos', titulo: 'Préstamos entre sedes', valor: (l) => l.prestamos },
  { clave: 'origen', titulo: 'Sale más de', valor: (l) => l.sede_origen_frecuente ?? '—' },
  { clave: 'destino', titulo: 'Va más a', valor: (l) => l.sede_destino_frecuente ?? '—' },
];

export function LibrosMasSolicitados() {
  const control = useFiltrosDeReporte(['desde', 'hasta', 'categoria_id', 'limite']);
  const { filtros } = control;
  const consulta = useReporte(
    'r3',
    librosMasSolicitados,
    {
      desde: filtros.desde,
      hasta: filtros.hasta,
      categoria_id: filtros.categoria_id,
      limite: filtros.limite,
    },
    { habilitado: !control.rangoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Ranking por préstamos interbibliotecarios no cancelados solicitados en el período.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros de libros más solicitados" control={control}>
        <FiltroCategoria
          valor={filtros.categoria_id}
          onCambiar={(categoria_id) => control.cambiar({ categoria_id })}
        />
        <FiltroSelect
          etiqueta="Mostrar"
          valor={filtros.limite ?? ''}
          onCambiar={(limite) => control.cambiar({ limite })}
        >
          <option value="">10 primeros</option>
          <option value="25">25 primeros</option>
          <option value="50">50 primeros</option>
        </FiltroSelect>
      </FiltrosConPeriodo>
      <Resultado consulta={consulta} vacio={(d) => d.libros.length === 0}>
        {(d) => (
          <Tabla
            etiqueta="Libros más solicitados"
            nombre="libros-mas-solicitados"
            columnas={COLUMNAS_R3}
            filas={d.libros}
            idDe={(l) => l.libro_id}
          />
        )}
      </Resultado>
    </div>
  );
}

// --- R4 --------------------------------------------------------------------------------------

const COLUMNAS_VENCIDOS = [
  {
    clave: 'numero',
    titulo: 'Préstamo',
    valor: (v) => v.numero,
    render: (v) => (
      <Link to={`/prestamos/${v.prestamo_id}`} className="mono">
        {v.numero}
      </Link>
    ),
  },
  { clave: 'socio', titulo: 'Socio', valor: (v) => `${v.socio} (${v.numero_socio})` },
  { clave: 'libro', titulo: 'Libro', valor: (v) => v.libro },
  { clave: 'sede', titulo: 'Sede', valor: (v) => v.sede },
  { clave: 'vence', titulo: 'Venció', valor: (v) => formatearFecha(v.fecha_vencimiento) },
  { clave: 'dias', titulo: 'Días de atraso', valor: (v) => v.dias_atraso },
  { clave: 'multa', titulo: 'Multa a hoy', valor: (v) => formatearMonto(v.multa_acumulada) },
];

const COLUMNAS_MULTAS = [
  {
    clave: 'numero',
    titulo: 'Préstamo',
    valor: (m) => m.numero_prestamo,
    render: (m) => (
      <Link to={`/prestamos/${m.prestamo_id}`} className="mono">
        {m.numero_prestamo}
      </Link>
    ),
  },
  { clave: 'socio', titulo: 'Socio', valor: (m) => m.socio },
  { clave: 'libro', titulo: 'Libro', valor: (m) => m.libro },
  { clave: 'dias', titulo: 'Días de atraso', valor: (m) => m.dias_atraso },
  { clave: 'monto', titulo: 'Monto', valor: (m) => formatearMonto(m.monto_total) },
  { clave: 'fecha', titulo: 'Generada', valor: (m) => formatearFecha(m.fecha_generacion) },
  {
    clave: 'estado',
    titulo: 'Estado',
    valor: (m) => estadoDe('multa', m.estado).texto,
    render: (m) => <EstadoBadge entidad="multa" estado={m.estado} />,
  },
];

export function VencidosYMultas() {
  const control = useFiltrosDeReporte(['desde', 'hasta', 'sede_id', 'estado_multa']);
  const { filtros } = control;
  const consulta = useReporte(
    'r4',
    vencidosYMultas,
    {
      desde: filtros.desde,
      hasta: filtros.hasta,
      sede_id: filtros.sede_id,
      estado_multa: filtros.estado_multa,
    },
    { habilitado: !control.rangoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Préstamos vencidos a hoy con la multa que llevan acumulada, y las multas generadas (el
        período filtra las multas por su fecha).
      </p>
      <FiltrosConPeriodo etiqueta="Filtros de vencidos y multas" control={control}>
        <FiltroSede valor={filtros.sede_id} onCambiar={(sede_id) => control.cambiar({ sede_id })} />
        <FiltroSelect
          etiqueta="Multas"
          valor={filtros.estado_multa ?? ''}
          onCambiar={(estado_multa) => control.cambiar({ estado_multa })}
        >
          <option value="">Todas</option>
          {Object.entries(ESTADOS.multa).map(([valor, { texto }]) => (
            <option key={valor} value={valor}>
              {texto}
            </option>
          ))}
        </FiltroSelect>
      </FiltrosConPeriodo>
      <Resultado
        consulta={consulta}
        vacio={(d) => d.vencidos.length === 0 && d.multas.length === 0}
      >
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Préstamos vencidos', valor: d.vencidos.length },
                {
                  etiqueta: 'Acumulado de vencidos',
                  valor: formatearMonto(d.total_acumulado_vencidos),
                },
                { etiqueta: 'Multas pendientes', valor: formatearMonto(d.total_multas_pendientes) },
                { etiqueta: 'Total adeudado', valor: formatearMonto(d.total_adeudado) },
              ]}
            />
            {d.vencidos.length > 0 && (
              <Tabla
                etiqueta="Préstamos vencidos"
                nombre="prestamos-vencidos"
                columnas={COLUMNAS_VENCIDOS}
                filas={d.vencidos}
                idDe={(v) => v.prestamo_id}
              />
            )}
            {d.multas.length > 0 && (
              <Tabla
                etiqueta="Multas"
                nombre="multas"
                columnas={COLUMNAS_MULTAS}
                filas={d.multas}
                idDe={(m) => m.multa_id}
              />
            )}
          </>
        )}
      </Resultado>
    </div>
  );
}

// --- R5 --------------------------------------------------------------------------------------

const COLUMNAS_R5 = [
  {
    clave: 'titulo',
    titulo: 'Libro',
    valor: (f) => f.titulo,
    render: (f) => <Link to={`/catalogo/${f.libro_id}`}>{f.titulo}</Link>,
  },
  { clave: 'sede', titulo: 'Sede', valor: (f) => f.sede },
  { clave: 'totales', titulo: 'Totales', valor: (f) => f.totales },
  { clave: 'disponibles', titulo: 'Disponibles', valor: (f) => f.disponibles },
  { clave: 'prestados', titulo: 'Prestados', valor: (f) => f.prestados },
  { clave: 'reservados', titulo: 'Reservados', valor: (f) => f.reservados },
  { clave: 'en_transito', titulo: 'En tránsito', valor: (f) => f.en_transito },
  { clave: 'otros', titulo: 'Otros', valor: (f) => f.otros },
];

export function DisponibilidadPorSede() {
  const control = useFiltrosDeReporte(['sede_id', 'categoria_id', 'page']);
  const { filtros } = control;
  const consulta = useReporte('r5', disponibilidadPorSede, {
    sede_id: filtros.sede_id,
    categoria_id: filtros.categoria_id,
    page: filtros.page,
  });
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Ejemplares activos de cada libro en su sede: cuántos hay y en qué situación están.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros de disponibilidad" control={control} conPeriodo={false}>
        <FiltroSede
          paraTodos
          valor={filtros.sede_id}
          onCambiar={(sede_id) => control.cambiar({ sede_id })}
        />
        <FiltroCategoria
          valor={filtros.categoria_id}
          onCambiar={(categoria_id) => control.cambiar({ categoria_id })}
        />
      </FiltrosConPeriodo>
      <Resultado consulta={consulta} vacio={(d) => d.items.length === 0}>
        {(d) => (
          <>
            <Tabla
              etiqueta="Disponibilidad por sede"
              nombre="disponibilidad-por-sede"
              columnas={COLUMNAS_R5}
              filas={d.items}
              idDe={(f) => `${f.libro_id}-${f.sede_id}`}
            />
            <Pagination
              page={d.page}
              size={d.size}
              total={d.total}
              onPage={(page) => control.cambiar({ page })}
            />
          </>
        )}
      </Resultado>
    </div>
  );
}

// --- R6 --------------------------------------------------------------------------------------

const COLUMNAS_ACTIVOS = [
  {
    clave: 'numero',
    titulo: 'Préstamo',
    valor: (p) => p.numero,
    render: (p) => (
      <Link to={`/prestamos/${p.prestamo_id}`} className="mono">
        {p.numero}
      </Link>
    ),
  },
  { clave: 'socio', titulo: 'Socio', valor: (p) => p.socio },
  { clave: 'libro', titulo: 'Libro', valor: (p) => p.libro },
  { clave: 'tipo', titulo: 'Tipo', valor: (p) => TIPOS_DE_PRESTAMO[p.tipo] },
  {
    clave: 'ruta',
    titulo: 'Origen → destino',
    valor: (p) => `${p.sede_origen} → ${p.sede_destino}`,
  },
  { clave: 'vence', titulo: 'Vence', valor: (p) => formatearFecha(p.fecha_vencimiento) },
  {
    clave: 'faltan',
    titulo: 'Días para vencer',
    valor: (p) =>
      p.dias_para_vencer < 0 ? `Venció hace ${-p.dias_para_vencer}` : p.dias_para_vencer,
  },
  {
    clave: 'estado',
    titulo: 'Estado',
    valor: (p) => estadoDe('prestamo', p.estado).texto,
    render: (p) => <EstadoBadge entidad="prestamo" estado={p.estado} />,
  },
];

const COLUMNAS_REMITOS = [
  {
    clave: 'numero',
    titulo: 'Remito',
    valor: (r) => r.numero,
    render: (r) => (
      <Link to={`/remitos/${r.remito_id}`} className="mono">
        {r.numero}
      </Link>
    ),
  },
  { clave: 'motivo', titulo: 'Motivo', valor: (r) => MOTIVOS_DE_REMITO[r.motivo] },
  { clave: 'origen', titulo: 'Origen', valor: (r) => r.sede_origen },
  { clave: 'destino', titulo: 'Destino', valor: (r) => r.sede_destino },
  { clave: 'ejemplares', titulo: 'Ejemplares', valor: (r) => r.ejemplares },
  { clave: 'antiguedad', titulo: 'Antigüedad (días)', valor: (r) => r.antiguedad_dias },
  {
    clave: 'estado',
    titulo: 'Estado',
    valor: (r) => estadoDe('remito', r.estado).texto,
    render: (r) => <EstadoBadge entidad="remito" estado={r.estado} />,
  },
];

export function ActivosYEnTransito() {
  const control = useFiltrosDeReporte(['sede_id']);
  const { filtros } = control;
  const consulta = useReporte('r6', activosYEnTransito, { sede_id: filtros.sede_id });
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Lo que está fuera de los estantes ahora: préstamos en manos de socios y remitos abiertos.
      </p>
      <FiltrosConPeriodo
        etiqueta="Filtros de activos y en tránsito"
        control={control}
        conPeriodo={false}
      >
        <FiltroSede valor={filtros.sede_id} onCambiar={(sede_id) => control.cambiar({ sede_id })} />
      </FiltrosConPeriodo>
      <Resultado
        consulta={consulta}
        vacio={(d) => d.prestamos.length === 0 && d.remitos.length === 0}
      >
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Préstamos en curso', valor: d.prestamos.length },
                {
                  etiqueta: 'Vencidos',
                  valor: d.prestamos.filter((p) => p.estado === 'VENCIDO').length,
                },
                { etiqueta: 'Remitos abiertos', valor: d.remitos.length },
              ]}
            />
            {d.prestamos.length > 0 && (
              <Tabla
                etiqueta="Préstamos en curso"
                nombre="prestamos-en-curso"
                columnas={COLUMNAS_ACTIVOS}
                filas={d.prestamos}
                idDe={(p) => p.prestamo_id}
              />
            )}
            {d.remitos.length > 0 && (
              <Tabla
                etiqueta="Remitos abiertos"
                nombre="remitos-abiertos"
                columnas={COLUMNAS_REMITOS}
                filas={d.remitos}
                idDe={(r) => r.remito_id}
              />
            )}
          </>
        )}
      </Resultado>
    </div>
  );
}
