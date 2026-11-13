"""Repositorios del catálogo sobre SQLAlchemy."""

from typing import Any

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    AutorORM,
    CategoriaORM,
    EjemplarORM,
    LibroAutorORM,
    LibroORM,
    MovimientoEjemplarORM,
    SedeORM,
)
from app.exceptions import EjemplarCodigoDuplicado, LibroDuplicado
from app.models.ejemplar import Ejemplar, EstadoFisico, MovimientoEjemplar
from app.models.libro import (
    CategoriaRef,
    DatosLibro,
    DisponibilidadLibro,
    DisponibilidadSede,
    Isbn,
    Libro,
    TipoMaterial,
)
from app.models.states.ejemplar import EstadoEjemplarEnum, estado_ejemplar
from app.models.usuario import UsuarioRef
from app.repositories.impl.consultas import nombres_de_usuarios, sin_tildes
from app.repositories.interfaces.catalogo_repository import FiltroEjemplares, FiltroLibros
from app.utils.texto import normalizar

_BAJA = EstadoEjemplarEnum.BAJA.value


def _restriccion(error: IntegrityError) -> str | None:
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


# --- categorías ----------------------------------------------------------------------------------


class SqlAlchemyCategoriaRepository:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def obtener(self, categoria_id: int) -> CategoriaRef | None:
        orm = self._sesion.get(CategoriaORM, categoria_id)
        return CategoriaRef(orm.id, orm.nombre) if orm else None

    def listar(self) -> list[CategoriaRef]:
        filas = self._sesion.scalars(select(CategoriaORM).order_by(CategoriaORM.nombre))
        return [CategoriaRef(f.id, f.nombre) for f in filas]


# --- libros --------------------------------------------------------------------------------------


def _libro_a_dominio(
    orm: LibroORM, nombres: dict[int, str], conteos: tuple[int, int] = (0, 0)
) -> Libro:
    def ref(usuario_id: int | None) -> UsuarioRef | None:
        if usuario_id is None:
            return None
        return UsuarioRef(usuario_id, nombres.get(usuario_id, "Usuario eliminado"))

    datos = DatosLibro(
        isbn=Isbn(orm.isbn) if orm.isbn else None,
        titulo=orm.titulo,
        autores=tuple(la.autor.nombre for la in orm.autores),
        editorial=orm.editorial,
        anio_edicion=orm.anio_edicion,
        categoria=CategoriaRef(orm.categoria.id, orm.categoria.nombre),
        tipo_material=TipoMaterial(orm.tipo_material),
    )
    return Libro(
        id=orm.id,
        datos=datos,
        creado_en=orm.creado_en,
        creado_por=ref(orm.creado_por_id),
        actualizado_en=orm.actualizado_en,
        actualizado_por=ref(orm.actualizado_por_id),
        cantidad_ejemplares=conteos[0],
        disponibles=conteos[1],
    )


class SqlAlchemyLibroRepository:
    """Implementa ``LibroRepository``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, libro_id: int) -> Libro | None:
        return self._uno(select(LibroORM).where(LibroORM.id == libro_id))

    def obtener_para_modificar(self, libro_id: int) -> Libro | None:
        consulta = (
            select(LibroORM)
            .where(LibroORM.id == libro_id)
            .with_for_update(of=LibroORM)
            .execution_options(populate_existing=True)
        )
        return self._uno(consulta)

    def buscar_duplicado(
        self, isbn: str | None, clave_natural: str | None, excluir_id: int | None = None
    ) -> Libro | None:
        if isbn:
            condicion: ColumnElement[bool] = LibroORM.isbn == isbn
        elif clave_natural:
            condicion = LibroORM.clave_natural == clave_natural
        else:
            return None
        consulta = select(LibroORM).where(condicion)
        if excluir_id is not None:
            consulta = consulta.where(LibroORM.id != excluir_id)
        return self._uno(consulta)

    def listar(self, filtro: FiltroLibros, page: int, size: int) -> tuple[list[Libro], int]:
        condiciones = self._condiciones(filtro)
        total = self._sesion.scalar(select(func.count(LibroORM.id)).where(*condiciones))
        filas = list(
            self._sesion.scalars(
                select(LibroORM)
                .where(*condiciones)
                .order_by(LibroORM.titulo_normalizado, LibroORM.id)
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return self._mapear(filas), total or 0

    def disponibilidad(self, libro_id: int) -> DisponibilidadLibro:
        libro = self._sesion.get(LibroORM, libro_id)
        assert libro is not None

        def contar(estado: EstadoEjemplarEnum) -> Any:
            return func.count(case((EjemplarORM.estado == estado.value, 1)))

        filas = self._sesion.execute(
            select(
                SedeORM.id,
                SedeORM.nombre,
                func.count(EjemplarORM.id),
                contar(EstadoEjemplarEnum.DISPONIBLE),
                contar(EstadoEjemplarEnum.PRESTADO),
                contar(EstadoEjemplarEnum.RESERVADO),
                contar(EstadoEjemplarEnum.EN_TRANSITO),
            )
            .join(SedeORM, SedeORM.id == EjemplarORM.sede_propietaria_id)
            .where(
                EjemplarORM.libro_id == libro_id,
                EjemplarORM.estado != _BAJA,
                SedeORM.estado == "ACTIVA",
            )
            .group_by(SedeORM.id, SedeORM.nombre)
            .order_by(SedeORM.nombre)
        ).all()
        por_sede = [
            DisponibilidadSede(
                sede_id=f[0],
                sede=f[1],
                totales=f[2],
                disponibles=f[3],
                prestados=f[4],
                reservados=f[5],
                en_transito=f[6],
                otros=f[2] - f[3] - f[4] - f[5] - f[6],
            )
            for f in filas
        ]
        return DisponibilidadLibro(libro_id=libro.id, titulo=libro.titulo, por_sede=por_sede)

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, libro: Libro) -> None:
        orm = LibroORM(creado_por_id=libro.creado_por.id if libro.creado_por else None)
        if libro.creado_en is not None:
            orm.creado_en = libro.creado_en
        self._copiar(libro, orm)
        self._persistir(lambda: self._sesion.add(orm))
        libro.id = orm.id

    def guardar(self, libro: Libro) -> None:
        assert libro.id is not None
        orm = self._sesion.get(LibroORM, libro.id)
        assert orm is not None
        self._copiar(libro, orm)
        self._persistir(lambda: None)

    def eliminar(self, libro_id: int) -> None:
        orm = self._sesion.get(LibroORM, libro_id)
        if orm is not None:
            self._sesion.delete(orm)
            self._sesion.flush()

    # --- internos -------------------------------------------------------------------------

    def _copiar(self, libro: Libro, orm: LibroORM) -> None:
        datos = libro.datos
        orm.isbn = datos.isbn.valor if datos.isbn else None
        orm.titulo = datos.titulo
        orm.titulo_normalizado = normalizar(datos.titulo)
        orm.editorial = datos.editorial
        orm.anio_edicion = datos.anio_edicion
        orm.categoria_id = datos.categoria.id
        orm.tipo_material = datos.tipo_material.value
        orm.clave_natural = datos.clave_natural
        if libro.actualizado_en is not None:
            orm.actualizado_en = libro.actualizado_en
        orm.actualizado_por_id = libro.actualizado_por.id if libro.actualizado_por else None
        actuales = [la.autor.nombre for la in orm.autores]
        if actuales != list(datos.autores):
            orm.autores.clear()
            self._sesion.flush()
            orm.autores.extend(
                LibroAutorORM(autor=self._autor(nombre), orden=i)
                for i, nombre in enumerate(datos.autores, start=1)
            )

    def _autor(self, nombre: str) -> AutorORM:
        clave = normalizar(nombre)
        autor = self._sesion.scalar(select(AutorORM).where(AutorORM.nombre_normalizado == clave))
        if autor is None:
            autor = AutorORM(nombre=nombre, nombre_normalizado=clave)
            self._sesion.add(autor)
        return autor

    def _persistir(self, preparar: Any) -> None:
        try:
            with self._sesion.begin_nested():
                preparar()
                self._sesion.flush()
        except IntegrityError as error:
            if _restriccion(error) not in ("uq_libro_isbn", "uq_libro_clave_natural"):
                raise
            raise LibroDuplicado(
                "Ya existe un libro con ese ISBN o con el mismo título, autor, editorial y año.",
                [{"campo": "isbn", "problema": "duplicado"}],
            ) from error

    def _uno(self, consulta: Any) -> Libro | None:
        orm = self._sesion.scalars(consulta).first()
        return self._mapear([orm])[0] if orm is not None else None

    def _mapear(self, filas: list[LibroORM]) -> list[Libro]:
        if not filas:
            return []
        ids: set[int] = set()
        for fila in filas:
            ids.update(i for i in (fila.creado_por_id, fila.actualizado_por_id) if i is not None)
        nombres = nombres_de_usuarios(self._sesion, ids)
        conteos = {
            libro_id: (totales, disponibles)
            for libro_id, totales, disponibles in self._sesion.execute(
                select(
                    EjemplarORM.libro_id,
                    func.count(EjemplarORM.id),
                    func.count(
                        case(
                            (
                                (EjemplarORM.estado == EstadoEjemplarEnum.DISPONIBLE.value)
                                & (SedeORM.estado == "ACTIVA"),
                                1,
                            )
                        )
                    ),
                )
                .join(SedeORM, SedeORM.id == EjemplarORM.sede_propietaria_id)
                .where(
                    EjemplarORM.libro_id.in_([f.id for f in filas]),
                    EjemplarORM.estado != _BAJA,
                )
                .group_by(EjemplarORM.libro_id)
            ).all()
        }
        return [_libro_a_dominio(f, nombres, conteos.get(f.id, (0, 0))) for f in filas]

    @staticmethod
    def _condiciones(filtro: FiltroLibros) -> list[ColumnElement[bool]]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.categoria_id is not None:
            condiciones.append(LibroORM.categoria_id == filtro.categoria_id)
        if filtro.tipo_material is not None:
            condiciones.append(LibroORM.tipo_material == filtro.tipo_material.value)
        if filtro.texto:
            por_autor = (
                select(LibroAutorORM.libro_id)
                .join(AutorORM, AutorORM.id == LibroAutorORM.autor_id)
                .where(AutorORM.nombre_normalizado.contains(filtro.texto, autoescape=True))
            )
            digitos = filtro.texto.replace("-", "").replace(" ", "").upper()
            condiciones.append(
                or_(
                    LibroORM.titulo_normalizado.contains(filtro.texto, autoescape=True),
                    LibroORM.id.in_(por_autor),
                    LibroORM.isbn.contains(digitos, autoescape=True),
                )
            )
        return condiciones


# --- ejemplares ----------------------------------------------------------------------------------


def _ejemplar_a_dominio(orm: EjemplarORM) -> Ejemplar:
    return Ejemplar(
        id=orm.id,
        codigo_inventario=orm.codigo_inventario,
        libro_id=orm.libro_id,
        sede_propietaria_id=orm.sede_propietaria_id,
        sede_actual_id=orm.sede_actual_id,
        estado_fisico=EstadoFisico(orm.estado_fisico),
        estado=estado_ejemplar(orm.estado),
        observaciones=orm.observaciones,
        fecha_baja=orm.fecha_baja,
        motivo_baja=orm.motivo_baja,
        version=orm.version,
        libro_titulo=orm.libro.titulo if orm.libro else None,
        sede_propietaria_nombre=orm.sede_propietaria.nombre if orm.sede_propietaria else None,
        sede_actual_nombre=orm.sede_actual.nombre if orm.sede_actual else None,
    )


class SqlAlchemyEjemplarRepository:
    """Implementa ``EjemplarRepository``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, ejemplar_id: int) -> Ejemplar | None:
        orm = self._sesion.get(EjemplarORM, ejemplar_id)
        return _ejemplar_a_dominio(orm) if orm else None

    def obtener_para_modificar(self, ejemplar_id: int) -> Ejemplar | None:
        orm = self._sesion.scalars(
            select(EjemplarORM)
            .where(EjemplarORM.id == ejemplar_id)
            .with_for_update(of=EjemplarORM)
            .execution_options(populate_existing=True)
        ).first()
        return _ejemplar_a_dominio(orm) if orm else None

    def obtener_por_codigo(self, codigo: str) -> Ejemplar | None:
        orm = self._sesion.scalar(
            select(EjemplarORM).where(EjemplarORM.codigo_inventario == codigo)
        )
        return _ejemplar_a_dominio(orm) if orm else None

    def listar(self, filtro: FiltroEjemplares, page: int, size: int) -> tuple[list[Ejemplar], int]:
        condiciones: list[ColumnElement[bool]] = []
        if filtro.sede_id is not None:
            condiciones.append(
                (EjemplarORM.sede_propietaria_id == filtro.sede_id)
                | (EjemplarORM.sede_actual_id == filtro.sede_id)
            )
        if filtro.libro_id is not None:
            condiciones.append(EjemplarORM.libro_id == filtro.libro_id)
        if filtro.estado is not None:
            condiciones.append(EjemplarORM.estado == filtro.estado.value)
        if filtro.codigo:
            condiciones.append(
                EjemplarORM.codigo_inventario.contains(filtro.codigo.upper(), autoescape=True)
            )
        return self._pagina(condiciones, page, size)

    def historial(self, ejemplar_id: int) -> list[MovimientoEjemplar]:
        filas = list(
            self._sesion.scalars(
                select(MovimientoEjemplarORM)
                .where(MovimientoEjemplarORM.ejemplar_id == ejemplar_id)
                .order_by(MovimientoEjemplarORM.fecha_hora, MovimientoEjemplarORM.id)
            )
        )
        nombres = nombres_de_usuarios(
            self._sesion, (f.usuario_id for f in filas if f.usuario_id is not None)
        )
        return [
            MovimientoEjemplar(
                estado_anterior=(
                    EstadoEjemplarEnum(f.estado_anterior) if f.estado_anterior else None
                ),
                estado_nuevo=EstadoEjemplarEnum(f.estado_nuevo),
                fecha_hora=f.fecha_hora,
                usuario=(
                    UsuarioRef(f.usuario_id, nombres.get(f.usuario_id, "Usuario eliminado"))
                    if f.usuario_id is not None
                    else None
                ),
                observacion=f.observacion,
            )
            for f in filas
        ]

    def disponibles_en_sede(self, libro_id: int, sede_id: int) -> int:
        consulta = select(func.count(EjemplarORM.id)).where(
            EjemplarORM.libro_id == libro_id,
            EjemplarORM.sede_actual_id == sede_id,
            EjemplarORM.estado == EstadoEjemplarEnum.DISPONIBLE.value,
        )
        return self._sesion.scalar(consulta) or 0

    def activos_de_libro(self, libro_id: int) -> int:
        consulta = (
            select(func.count(EjemplarORM.id))
            .join(SedeORM, SedeORM.id == EjemplarORM.sede_propietaria_id)
            .where(
                EjemplarORM.libro_id == libro_id,
                EjemplarORM.estado != _BAJA,
                SedeORM.estado == "ACTIVA",
            )
        )
        return self._sesion.scalar(consulta) or 0

    def contar_de_libro(self, libro_id: int) -> int:
        return (
            self._sesion.scalar(
                select(func.count(EjemplarORM.id)).where(EjemplarORM.libro_id == libro_id)
            )
            or 0
        )

    def alojados_en_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        condiciones = [EjemplarORM.sede_actual_id == sede_id, EjemplarORM.estado != _BAJA]
        return self._pagina(condiciones, 1, limite)

    def propios_fuera_de_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        condiciones = [
            EjemplarORM.sede_propietaria_id == sede_id,
            EjemplarORM.estado != _BAJA,
            (EjemplarORM.sede_actual_id != sede_id)
            | (EjemplarORM.estado == EstadoEjemplarEnum.EN_TRANSITO.value),
        ]
        return self._pagina(condiciones, 1, limite)

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, ejemplar: Ejemplar) -> None:
        orm = EjemplarORM(codigo_inventario=ejemplar.codigo_inventario, libro_id=ejemplar.libro_id)
        self._copiar(ejemplar, orm)

        def preparar() -> None:
            self._sesion.add(orm)
            self._sesion.flush()
            ejemplar.id = orm.id
            self._movimientos(ejemplar)

        self._persistir(preparar)

    def guardar(self, ejemplar: Ejemplar) -> None:
        assert ejemplar.id is not None
        orm = self._sesion.get(EjemplarORM, ejemplar.id)
        assert orm is not None
        self._copiar(ejemplar, orm)
        self._persistir(lambda: self._movimientos(ejemplar))

    # --- internos -------------------------------------------------------------------------

    def _pagina(
        self, condiciones: list[ColumnElement[bool]], page: int, size: int
    ) -> tuple[list[Ejemplar], int]:
        total = self._sesion.scalar(select(func.count(EjemplarORM.id)).where(*condiciones))
        filas = self._sesion.scalars(
            select(EjemplarORM)
            .join(LibroORM, LibroORM.id == EjemplarORM.libro_id)
            .where(*condiciones)
            .order_by(sin_tildes(LibroORM.titulo), EjemplarORM.codigo_inventario)
            .offset((page - 1) * size)
            .limit(size)
        )
        return [_ejemplar_a_dominio(f) for f in filas], total or 0

    @staticmethod
    def _copiar(ejemplar: Ejemplar, orm: EjemplarORM) -> None:
        orm.sede_propietaria_id = ejemplar.sede_propietaria_id
        orm.sede_actual_id = ejemplar.sede_actual_id
        orm.estado_fisico = ejemplar.estado_fisico.value
        orm.estado = ejemplar.estado_nombre.value
        orm.observaciones = ejemplar.observaciones
        orm.fecha_baja = ejemplar.fecha_baja
        orm.motivo_baja = ejemplar.motivo_baja
        orm.version = ejemplar.version

    def _movimientos(self, ejemplar: Ejemplar) -> None:
        assert ejemplar.id is not None
        for mov in ejemplar.movimientos_pendientes:
            self._sesion.add(
                MovimientoEjemplarORM(
                    ejemplar_id=ejemplar.id,
                    estado_anterior=mov.estado_anterior.value if mov.estado_anterior else None,
                    estado_nuevo=mov.estado_nuevo.value,
                    fecha_hora=mov.fecha_hora,
                    usuario_id=mov.usuario.id if mov.usuario else None,
                    observacion=mov.observacion,
                )
            )
        ejemplar.movimientos_pendientes.clear()
        self._sesion.flush()

    def _persistir(self, preparar: Any) -> None:
        try:
            with self._sesion.begin_nested():
                preparar()
                self._sesion.flush()
        except IntegrityError as error:
            if _restriccion(error) != "uq_ejemplar_codigo_inventario":
                raise
            raise EjemplarCodigoDuplicado(
                "Ya existe un ejemplar con ese código de inventario en la red.",
                [{"campo": "codigo_inventario", "problema": "duplicado"}],
            ) from error
