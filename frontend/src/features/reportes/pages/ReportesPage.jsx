import { useSesion } from '../../../auth/SesionContext.jsx';
import { PageHeader, Tabs } from '../../../components/index.js';
import { useFiltrosUrl } from '../../../hooks/useFiltrosUrl.js';
import { useTituloDePagina } from '../../../hooks/useTituloDePagina.js';
import { PERMISOS } from '../../../utils/roles.js';
import {
  ActivosYEnTransito,
  DisponibilidadPorSede,
  EnviosEIncidencias,
  LibrosMasSolicitados,
  MovimientoEntreSedes,
  VencidosYMultas,
} from '../components/Reportes.jsx';

/** Reportes R1 a R6; cada rol ve solo los que puede emitir (RF-REP-08). */
const REPORTES = [
  {
    id: 'r1',
    titulo: 'Movimiento entre sedes',
    permiso: PERMISOS.REPORTE_SEDE,
    Componente: MovimientoEntreSedes,
  },
  {
    id: 'r2',
    titulo: 'Envíos e incidencias',
    permiso: PERMISOS.REPORTE_RED,
    Componente: EnviosEIncidencias,
  },
  {
    id: 'r3',
    titulo: 'Libros más pedidos',
    permiso: PERMISOS.REPORTE_RED,
    Componente: LibrosMasSolicitados,
  },
  {
    id: 'r4',
    titulo: 'Vencidos y multas',
    permiso: PERMISOS.REPORTE_SEDE,
    Componente: VencidosYMultas,
  },
  {
    id: 'r5',
    titulo: 'Disponibilidad',
    permiso: PERMISOS.CATALOGO_LEER,
    Componente: DisponibilidadPorSede,
  },
  {
    id: 'r6',
    titulo: 'Activos y en tránsito',
    permiso: PERMISOS.REPORTE_SEDE,
    Componente: ActivosYEnTransito,
  },
];

export default function ReportesPage() {
  useTituloDePagina('Reportes');
  const { usuario, tienePermiso } = useSesion();
  const { filtros, cambiar } = useFiltrosUrl();
  const disponibles = REPORTES.filter((r) => tienePermiso(r.permiso));
  const activa = disponibles.some((r) => r.id === filtros.r) ? filtros.r : disponibles[0]?.id;
  const descripcion =
    usuario.rol === 'BIBLIOTECARIO'
      ? `Calculados con los datos registrados de ${usuario.sede?.nombre ?? 'su sede'}.`
      : 'Calculados con los datos registrados en toda la red.';

  return (
    <>
      <PageHeader titulo="Reportes" descripcion={descripcion} />
      <Tabs
        activa={activa}
        onCambiar={(r) => cambiar({ r, page: '' })}
        tabs={disponibles.map(({ id, titulo, Componente }) => ({
          id,
          titulo,
          contenido: <Componente />,
        }))}
      />
    </>
  );
}
