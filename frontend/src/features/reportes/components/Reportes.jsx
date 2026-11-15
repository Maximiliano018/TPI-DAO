import { Link } from 'react-router-dom';
import {
  Alert,
  BusquedaConEspera,
  FiltroNumero,
  FiltroSelect,
  Pagination,
  Table,
} from '../../../components/index.js';
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
import FiltroSocio from '../../socios/components/FiltroSocio.jsx';
import {
  BotonCsv,
  FiltroSede,
  FiltrosConPeriodo,
  Indicadores,
  Resultado,
  Seccion,
  todasLasPaginas,
  useFiltrosDeReporte,
  useReporte,
} from './comunes.jsx';
import estilos from './Reportes.module.css';

const porcentaje = (tasa) => (tasa === null ? '—' : `${Math.round(tasa * 1000) / 10} %`);

/** Columnas compartidas por la tabla y el CSV: `valor` es el texto; `render`, lo que se ve. */
const aTabla = (columnas) =>
  columnas.map(({ clave, titulo, valor, render }) => ({ clave, titulo, render: render ?? valor }));

/** Opciones de un selector a partir de un mapa `{ VALOR: 'Texto' }`. */
function Opciones({ todas, mapa }) {
  return (
    <>
      <option value="">{todas}</option>
      {Object.entries(mapa).map(([valor, texto]) => (
        <option key={valor} value={valor}>
          {texto}
        </option>
      ))}
    </>
  );
}

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

function Tabla({ etiqueta, nombre, columnas, filas, idDe, obtenerFilas }) {
  return (
    <Seccion
      titulo={etiqueta}
      acciones={
        <BotonCsv nombre={nombre} columnas={columnas} filas={filas} obtenerFilas={obtenerFilas} />
      }
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
  { clave: 'ejemplares', titulo: 'Ejemplares recibidos', valor: (r) => r.ejemplares },
  {
    clave: 'transito',
    titulo: 'Tránsito promedio (días)',
    valor: (r) => r.tiempo_promedio_transito_dias.toLocaleString('es-AR'),
  },
];

export function MovimientoEntreSedes() {
  const control = useFiltrosDeReporte([
    'desde',
    'hasta',
    'sede_id',
    'sede_origen_id',
    'sede_destino_id',
    'motivo',
  ]);
  const { filtros } = control;
  const consulta = useReporte(
    'r1',
    movimientoEntreSedes,
    {
      desde: filtros.desde,
      hasta: filtros.hasta,
      sede_id: filtros.sede_id,
      sede_origen_id: filtros.sede_origen_id,
      sede_destino_id: filtros.sede_destino_id,
      motivo: filtros.motivo,
    },
    { habilitado: !control.rangoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Remitos que llegaron a destino en el período, por ruta. El tránsito va del despacho a la
        recepción; los envíos que siguen en camino no entran y los ejemplares faltantes no cuentan
        como recibidos.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros del movimiento entre sedes" control={control}>
        <FiltroSede valor={filtros.sede_id} onCambiar={(sede_id) => control.cambiar({ sede_id })} />
        <FiltroSede
          paraTodos
          etiqueta="Origen"
          valor={filtros.sede_origen_id}
          onCambiar={(sede_origen_id) => control.cambiar({ sede_origen_id })}
        />
        <FiltroSede
          paraTodos
          etiqueta="Destino"
          valor={filtros.sede_destino_id}
          onCambiar={(sede_destino_id) => control.cambiar({ sede_destino_id })}
        />
        <FiltroSelect
          etiqueta="Motivo"
          valor={filtros.motivo ?? ''}
          onCambiar={(motivo) => control.cambiar({ motivo })}
        >
          <Opciones todas="Todos" mapa={MOTIVOS_DE_REMITO} />
        </FiltroSelect>
      </FiltrosConPeriodo>
      <Resultado consulta={consulta} vacio={(d) => d.rutas.length === 0}>
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Envíos recibidos', valor: d.total_envios },
                { etiqueta: 'Ejemplares recibidos', valor: d.total_ejemplares },
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

const columnasR2 = (tituloSede) => [
  { clave: 'sede', titulo: tituloSede, valor: (s) => s.sede },
  { clave: 'total', titulo: 'Envíos', valor: (s) => s.total_envios },
  { clave: 'recibidos', titulo: 'Recibidos', valor: (s) => s.recibidos },
  { clave: 'extraviados', titulo: 'Extraviados', valor: (s) => s.extraviados },
  { clave: 'danados', titulo: 'Dañados', valor: (s) => s.danados },
  { clave: 'destruidos', titulo: 'Destruidos', valor: (s) => s.destruidos },
  { clave: 'incompletos', titulo: 'Con faltantes', valor: (s) => s.incompletos },
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
              etiqueta="Envíos por sede origen"
              nombre="envios-por-sede-origen"
              columnas={columnasR2('Sede origen')}
              filas={d.por_sede}
              idDe={(s) => s.sede_id}
            />
            <Tabla
              etiqueta="Envíos por sede destino"
              nombre="envios-por-sede-destino"
              columnas={columnasR2('Sede destino')}
              filas={d.por_destino}
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
  const control = useFiltrosDeReporte(['desde', 'hasta', 'sede_id', 'categoria_id', 'limite']);
  const { filtros } = control;
  const consulta = useReporte(
    'r3',
    librosMasSolicitados,
    {
      desde: filtros.desde,
      hasta: filtros.hasta,
      sede_id: filtros.sede_id,
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
        <FiltroSede
          etiqueta="Sede (origen o destino)"
          valor={filtros.sede_id}
          onCambiar={(sede_id) => control.cambiar({ sede_id })}
        />
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
  {
    clave: 'sede',
    titulo: 'Sede',
    valor: (v) => (v.sede_origen === v.sede ? v.sede : `${v.sede_origen} → ${v.sede}`),
  },
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
  { clave: 'concepto', titulo: 'Concepto', valor: (m) => m.concepto },
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
  const control = useFiltrosDeReporte([
    'desde',
    'hasta',
    'sede_id',
    'socio_id',
    'estado_multa',
    'atraso_min',
    'atraso_max',
  ]);
  const { filtros } = control;
  const atrasoInvalido =
    filtros.atraso_min !== undefined &&
    filtros.atraso_min !== '' &&
    filtros.atraso_max !== undefined &&
    filtros.atraso_max !== '' &&
    Number(filtros.atraso_max) < Number(filtros.atraso_min);
  const consulta = useReporte(
    'r4',
    vencidosYMultas,
    {
      desde: filtros.desde,
      hasta: filtros.hasta,
      sede_id: filtros.sede_id,
      socio_id: filtros.socio_id,
      estado_multa: filtros.estado_multa,
      atraso_min: filtros.atraso_min,
      atraso_max: filtros.atraso_max,
    },
    { habilitado: !control.rangoInvalido && !atrasoInvalido },
  );
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Préstamos vencidos a hoy con la multa que llevan acumulada, y las multas generadas. El
        estado, el período (fecha de la multa) y los días de atraso acotan las tablas; los totales
        son siempre la deuda real de la sede o del socio elegidos.
      </p>
      <FiltroSocio
        socioId={filtros.socio_id}
        onCambiar={(socio_id) => control.cambiar({ socio_id })}
      />
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
        <FiltroNumero
          etiqueta="Atraso desde (días)"
          valor={filtros.atraso_min}
          onCambiar={(atraso_min) => control.cambiar({ atraso_min })}
        />
        <FiltroNumero
          etiqueta="Atraso hasta (días)"
          valor={filtros.atraso_max}
          onCambiar={(atraso_max) => control.cambiar({ atraso_max })}
        />
      </FiltrosConPeriodo>
      {atrasoInvalido && (
        <Alert tono="danger">El atraso «hasta» no puede ser menor que «desde».</Alert>
      )}
      <Resultado
        consulta={consulta}
        vacio={(d) =>
          d.vencidos.length === 0 &&
          d.multas.length === 0 &&
          d.cantidad_vencidos === 0 &&
          Number(d.total_adeudado) === 0
        }
      >
        {(d) => (
          <>
            <Indicadores
              items={[
                { etiqueta: 'Préstamos vencidos', valor: d.cantidad_vencidos },
                {
                  etiqueta: 'Acumulado de vencidos',
                  valor: formatearMonto(d.total_acumulado_vencidos),
                },
                { etiqueta: 'Multas pendientes', valor: formatearMonto(d.total_multas_pendientes) },
                { etiqueta: 'Total adeudado', valor: formatearMonto(d.total_adeudado) },
              ]}
            />
            {d.vencidos.length === 0 && d.multas.length === 0 && (
              <p className={estilos.descripcion}>
                Ningún préstamo vencido ni multa coincide con los filtros.
              </p>
            )}
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
  const control = useFiltrosDeReporte(['q', 'sede_id', 'categoria_id', 'page']);
  const { filtros } = control;
  const params = { q: filtros.q, sede_id: filtros.sede_id, categoria_id: filtros.categoria_id };
  const consulta = useReporte('r5', disponibilidadPorSede, { ...params, page: filtros.page });
  const limpios = Object.fromEntries(Object.entries(params).filter(([, v]) => v));
  return (
    <div className={estilos.reporte}>
      <p className={estilos.descripcion}>
        Ejemplares activos de cada libro en su sede: cuántos hay y en qué situación están. «Otros»
        son los apartados para un préstamo o un retorno y los que están en revisión.
      </p>
      <FiltrosConPeriodo etiqueta="Filtros de disponibilidad" control={control} conPeriodo={false}>
        <BusquedaConEspera
          etiqueta="Buscar por título, autor o ISBN"
          valor={filtros.q ?? ''}
          onBuscar={(q) => control.cambiar({ q, page: '' })}
        />
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
              obtenerFilas={() => todasLasPaginas(disponibilidadPorSede, limpios)}
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

const REMITOS_ABIERTOS = Object.fromEntries(
  ['GENERADO', 'EMPAQUETADO', 'DESPACHADO', 'EN_TRANSITO'].map((e) => [e, ESTADOS.remito[e].texto]),
);

export function ActivosYEnTransito() {
  const control = useFiltrosDeReporte(['sede_id', 'estado', 'tipo', 'estado_remito']);
  const { filtros } = control;
  const consulta = useReporte('r6', activosYEnTransito, {
    sede_id: filtros.sede_id,
    estado: filtros.estado,
    tipo: filtros.tipo,
    estado_remito: filtros.estado_remito,
  });
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
        <FiltroSelect
          etiqueta="Préstamos"
          valor={filtros.estado ?? ''}
          onCambiar={(estado) => control.cambiar({ estado })}
        >
          <Opciones todas="Todos" mapa={{ ACTIVO: 'Al día', VENCIDO: 'Vencidos' }} />
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Tipo de préstamo"
          valor={filtros.tipo ?? ''}
          onCambiar={(tipo) => control.cambiar({ tipo })}
        >
          <Opciones todas="Todos" mapa={TIPOS_DE_PRESTAMO} />
        </FiltroSelect>
        <FiltroSelect
          etiqueta="Estado del remito"
          valor={filtros.estado_remito ?? ''}
          onCambiar={(estado_remito) => control.cambiar({ estado_remito })}
        >
          <Opciones todas="Todos" mapa={REMITOS_ABIERTOS} />
        </FiltroSelect>
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
                  // Por fecha, como R4: aunque la tarea diaria todavía no los haya marcado.
                  valor: d.prestamos.filter((p) => p.dias_para_vencer < 0).length,
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
