"""Casos de uso del catálogo: libros, ejemplares y disponibilidad por sede."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from app.exceptions import (
    CategoriaInvalida,
    EjemplarCodigoDuplicado,
    EjemplarNoEncontrado,
    ErrorDeValidacion,
    LibroConEjemplares,
    LibroDuplicado,
    LibroNoEncontrado,
    PermisoDenegado,
)
from app.models.ejemplar import Ejemplar, EstadoFisico, MovimientoEjemplar
from app.models.libro import (
    CategoriaRef,
    DatosLibro,
    DisponibilidadLibro,
    Libro,
    TipoMaterial,
)
from app.models.paginacion import Pagina
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef
from app.repositories.interfaces.catalogo_repository import FiltroEjemplares, FiltroLibros
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.utils.reloj import Reloj
from app.utils.texto import normalizar


@dataclass(frozen=True)
class DatosLibroNuevo:
    """Datos de un libro tal como llegan de la API (sin validar)."""

    titulo: str
    autores: list[str]
    categoria_id: int
    tipo_material: TipoMaterial = TipoMaterial.LIBRO
    isbn: str | None = None
    editorial: str | None = None
    anio_edicion: int | None = None


@dataclass(frozen=True)
class DatosEjemplarNuevo:
    libro_id: int
    codigo_inventario: str
    estado_fisico: EstadoFisico = EstadoFisico.BUENO
    observaciones: str | None = None
    sede_id: int | None = None


@dataclass(frozen=True)
class DetalleEjemplar:
    ejemplar: Ejemplar
    historial: list[MovimientoEjemplar]


class CatalogoService:
    """Libros (solo el administrador) y ejemplares (el bibliotecario, los de su sede)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- libros ---------------------------------------------------------------------------

    def crear_libro(self, actor: Usuario, datos: DatosLibroNuevo) -> Libro:
        """Alta de un libro sin duplicados por ISBN o por clave natural (RF-CAT-01, 02).

        Raises:
            PermisoDenegado, ErrorDeValidacion, CategoriaInvalida.
            LibroDuplicado: Ya existe (``detalles`` trae el libro existente).
        """
        actor.exigir(Permiso.CATALOGO_ADMINISTRAR)
        validados = self._validar_libro(datos)
        with self._transaccion():
            self._rechazar_duplicado(validados)
            libro = Libro.crear(validados, actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.libros.agregar(libro)
        return libro

    def modificar_libro(self, actor: Usuario, libro_id: int, datos: DatosLibroNuevo) -> Libro:
        """Reemplaza los datos del libro (RF-CAT-01)."""
        actor.exigir(Permiso.CATALOGO_ADMINISTRAR)
        validados = self._validar_libro(datos)
        with self._transaccion():
            libro = self._libro_para_modificar(libro_id)
            self._rechazar_duplicado(validados, excluir_id=libro_id)
            if libro.modificar(validados, actor=_ref(actor), ahora=self._reloj.ahora()):
                self._uow.libros.guardar(libro)
        return libro

    def eliminar_libro(self, actor: Usuario, libro_id: int) -> None:
        """Elimina un libro cargado por error, solo si no tiene ejemplares (RF-CAT-08).

        Raises:
            LibroNoEncontrado.
            LibroConEjemplares: Tiene ejemplares (aunque estén dados de baja: son historial).
        """
        actor.exigir(Permiso.CATALOGO_ADMINISTRAR)
        with self._transaccion():
            libro = self._libro_para_modificar(libro_id)
            cantidad = self._uow.ejemplares.contar_de_libro(libro_id)
            if cantidad:
                raise LibroConEjemplares(
                    f"El libro «{libro.titulo}» tiene {cantidad} ejemplar(es) y no se puede "
                    "eliminar.",
                    [{"campo": "libro_id", "problema": "con_ejemplares", "cantidad": cantidad}],
                )
            self._uow.libros.eliminar(libro_id)

    def obtener_libro(self, actor: Usuario, libro_id: int) -> Libro:
        actor.exigir(Permiso.CATALOGO_LEER)
        libro = self._uow.libros.obtener(libro_id)
        if libro is None:
            raise LibroNoEncontrado("El libro solicitado no existe.")
        return libro

    def buscar_libros(
        self,
        actor: Usuario,
        texto: str | None,
        categoria_id: int | None,
        tipo_material: TipoMaterial | None,
        page: int,
        size: int,
    ) -> Pagina[Libro]:
        """Búsqueda por título, autor o ISBN, y por categoría (RF-CAT-09)."""
        actor.exigir(Permiso.CATALOGO_LEER)
        filtro = FiltroLibros(
            texto=normalizar(texto) if texto and texto.strip() else None,
            categoria_id=categoria_id,
            tipo_material=tipo_material,
        )
        libros, total = self._uow.libros.listar(filtro, page, size)
        return Pagina(libros, total, page, size)

    def disponibilidad(self, actor: Usuario, libro_id: int) -> DisponibilidadLibro:
        """Ejemplares por sede activa y por estado (RF-CAT-09, 10)."""
        self.obtener_libro(actor, libro_id)
        return self._uow.libros.disponibilidad(libro_id)

    def categorias(self, actor: Usuario) -> list[CategoriaRef]:
        actor.exigir(Permiso.CATALOGO_LEER)
        return self._uow.categorias.listar()

    # --- ejemplares -----------------------------------------------------------------------

    def crear_ejemplar(self, actor: Usuario, datos: DatosEjemplarNuevo) -> Ejemplar:
        """Alta de un ejemplar ``Disponible`` en una sede activa (RF-CAT-03, 04).

        El bibliotecario lo carga en su sede; el administrador indica la sede.

        Raises:
            PermisoDenegado, ErrorDeValidacion, LibroNoEncontrado.
            EjemplarCodigoDuplicado: El código ya existe en la red.
            SedeNoEncontrada, SedeEnBaja: La sede no existe o está dada de baja.
        """
        actor.exigir(Permiso.EJEMPLAR_ADMINISTRAR)
        sede_id = self._sede_del_alta(actor, datos.sede_id)
        with self._transaccion():
            libro = self._uow.libros.obtener(datos.libro_id)
            if libro is None:
                raise LibroNoEncontrado(
                    "El libro indicado no existe.",
                    [{"campo": "libro_id", "problema": "no_existe"}],
                )
            sede = self._uow.sedes.obtener_para_operar(sede_id)
            assert sede.id is not None
            ejemplar = Ejemplar.registrar(
                codigo_inventario=datos.codigo_inventario,
                libro_id=datos.libro_id,
                sede_id=sede.id,
                estado_fisico=datos.estado_fisico,
                observaciones=datos.observaciones,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            if self._uow.ejemplares.obtener_por_codigo(ejemplar.codigo_inventario):
                raise EjemplarCodigoDuplicado(
                    f"Ya existe el ejemplar {ejemplar.codigo_inventario} en la red.",
                    [{"campo": "codigo_inventario", "problema": "duplicado"}],
                )
            self._uow.ejemplares.agregar(ejemplar)
        assert ejemplar.id is not None
        # Se relee para devolverlo con el título del libro y los nombres de las sedes.
        return self._uow.ejemplares.obtener(ejemplar.id) or ejemplar

    def modificar_ejemplar(
        self,
        actor: Usuario,
        ejemplar_id: int,
        version: int,
        estado_fisico: EstadoFisico,
        observaciones: str | None,
    ) -> Ejemplar:
        """Cambia el estado físico y las observaciones; la disponibilidad no (CU-CAT-03).

        Raises:
            EjemplarNoEncontrado, PermisoDenegado (otra sede, CA-CAT-05), ConflictoDeVersion.
        """
        actor.exigir(Permiso.EJEMPLAR_ADMINISTRAR)
        with self._transaccion():
            ejemplar = self._ejemplar_para_modificar(actor, ejemplar_id)
            ejemplar.validar_version(version)
            if ejemplar.modificar(estado_fisico=estado_fisico, observaciones=observaciones):
                self._uow.ejemplares.guardar(ejemplar)
        return ejemplar

    def dar_de_baja_ejemplar(
        self, actor: Usuario, ejemplar_id: int, version: int, motivo: str
    ) -> Ejemplar:
        """Baja lógica de un ejemplar disponible o en revisión (RF-CAT-07)."""
        actor.exigir(Permiso.EJEMPLAR_ADMINISTRAR)
        with self._transaccion():
            ejemplar = self._ejemplar_para_modificar(actor, ejemplar_id)
            ejemplar.validar_version(version)
            ejemplar.dar_de_baja(motivo, _ref(actor), self._reloj.ahora())
            self._uow.ejemplares.guardar(ejemplar)
        return ejemplar

    def reparar_ejemplar(self, actor: Usuario, ejemplar_id: int, version: int) -> Ejemplar:
        """Un ejemplar en revisión vuelve a estar disponible (RF-DEV-10)."""
        actor.exigir(Permiso.EJEMPLAR_ADMINISTRAR)
        with self._transaccion():
            ejemplar = self._ejemplar_para_modificar(actor, ejemplar_id)
            ejemplar.validar_version(version)
            ejemplar.reparar(_ref(actor), self._reloj.ahora())
            self._uow.ejemplares.guardar(ejemplar)
            ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, _ref(actor))
        return ejemplar

    def detalle_ejemplar(self, actor: Usuario, ejemplar_id: int) -> DetalleEjemplar:
        """Ejemplar con su historial de estados (solo el personal, CU-CAT-05 A4)."""
        actor.exigir(Permiso.EJEMPLAR_LEER)
        ejemplar = self._uow.ejemplares.obtener(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado("El ejemplar solicitado no existe.")
        return DetalleEjemplar(ejemplar, self._uow.ejemplares.historial(ejemplar_id))

    def listar_ejemplares(
        self,
        actor: Usuario,
        sede_id: int | None,
        libro_id: int | None,
        estado: EstadoEjemplarEnum | None,
        codigo: str | None,
        page: int,
        size: int,
    ) -> Pagina[Ejemplar]:
        actor.exigir(Permiso.EJEMPLAR_LEER)
        filtro = FiltroEjemplares(sede_id=sede_id, libro_id=libro_id, estado=estado, codigo=codigo)
        ejemplares, total = self._uow.ejemplares.listar(filtro, page, size)
        return Pagina(ejemplares, total, page, size)

    # --- internos -------------------------------------------------------------------------

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()

    def _validar_libro(self, datos: DatosLibroNuevo) -> DatosLibro:
        categoria = self._uow.categorias.obtener(datos.categoria_id)
        if categoria is None:
            raise CategoriaInvalida(
                "Elija una categoría de la lista.",
                [{"campo": "categoria_id", "problema": "Elija una categoría de la lista."}],
            )
        return DatosLibro.crear(
            isbn=datos.isbn,
            titulo=datos.titulo,
            autores=datos.autores,
            editorial=datos.editorial,
            anio_edicion=datos.anio_edicion,
            categoria=categoria,
            tipo_material=datos.tipo_material,
            anio_actual=self._reloj.hoy().year,
        )

    def _rechazar_duplicado(self, datos: DatosLibro, excluir_id: int | None = None) -> None:
        existente = self._uow.libros.buscar_duplicado(
            datos.isbn.valor if datos.isbn else None, datos.clave_natural, excluir_id
        )
        if existente is None:
            return
        motivo = (
            f"el ISBN {datos.isbn.valor}"
            if datos.isbn
            else "el mismo título, autor, editorial y año"
        )
        raise LibroDuplicado(
            f"Ya existe el libro «{existente.titulo}» con {motivo}.",
            [
                {
                    "campo": "isbn" if datos.isbn else "titulo",
                    "problema": "duplicado",
                    "libro_id": existente.id,
                }
            ],
        )

    def _libro_para_modificar(self, libro_id: int) -> Libro:
        libro = self._uow.libros.obtener_para_modificar(libro_id)
        if libro is None:
            raise LibroNoEncontrado("El libro solicitado no existe.")
        return libro

    def _ejemplar_para_modificar(self, actor: Usuario, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._uow.ejemplares.obtener_para_modificar(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado("El ejemplar solicitado no existe.")
        if actor.rol == Rol.BIBLIOTECARIO and not actor.opera_en(ejemplar.sede_propietaria_id):
            raise PermisoDenegado("Solo puede administrar los ejemplares de su sede.")
        return ejemplar

    @staticmethod
    def _sede_del_alta(actor: Usuario, sede_id: int | None) -> int:
        if actor.rol == Rol.BIBLIOTECARIO:
            assert actor.sede_id is not None
            if sede_id is not None and sede_id != actor.sede_id:
                raise PermisoDenegado("Solo puede cargar ejemplares en su sede.")
            return actor.sede_id
        if sede_id is None:
            raise ErrorDeValidacion(
                "Indique la sede del ejemplar.",
                [{"campo": "sede_id", "problema": "obligatorio"}],
            )
        return sede_id


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
