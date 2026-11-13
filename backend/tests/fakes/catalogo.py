"""Repositorios del catálogo en memoria para las pruebas de servicios."""

from app.exceptions import EjemplarCodigoDuplicado, LibroDuplicado
from app.models.ejemplar import Ejemplar, MovimientoEjemplar
from app.models.libro import CategoriaRef, DisponibilidadLibro, DisponibilidadSede, Libro
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.repositories.interfaces.catalogo_repository import FiltroEjemplares, FiltroLibros
from app.utils.texto import normalizar

CATEGORIAS = [CategoriaRef(1, "Literatura argentina"), CategoriaRef(2, "Historia")]
_BAJA = EstadoEjemplarEnum.BAJA


class CategoriaRepositorioEnMemoria:
    def __init__(self, categorias: list[CategoriaRef] | None = None) -> None:
        self._categorias = {c.id: c for c in (categorias or CATEGORIAS)}

    def obtener(self, categoria_id: int) -> CategoriaRef | None:
        return self._categorias.get(categoria_id)

    def listar(self) -> list[CategoriaRef]:
        return sorted(self._categorias.values(), key=lambda c: c.nombre)


class EjemplarRepositorioEnMemoria:
    def __init__(self) -> None:
        self.ejemplares: dict[int, Ejemplar] = {}
        self.movimientos: dict[int, list[MovimientoEjemplar]] = {}

    def _persistir_movimientos(self, ejemplar: Ejemplar) -> None:
        assert ejemplar.id is not None
        self.movimientos.setdefault(ejemplar.id, []).extend(ejemplar.movimientos_pendientes)
        ejemplar.movimientos_pendientes.clear()

    def agregar(self, ejemplar: Ejemplar) -> None:
        if self.obtener_por_codigo(ejemplar.codigo_inventario):
            raise EjemplarCodigoDuplicado("Código repetido.")
        ejemplar.id = ejemplar.id or max(self.ejemplares, default=0) + 1
        self.ejemplares[ejemplar.id] = ejemplar
        self._persistir_movimientos(ejemplar)

    def guardar(self, ejemplar: Ejemplar) -> None:
        assert ejemplar.id in self.ejemplares
        self._persistir_movimientos(ejemplar)

    def obtener(self, ejemplar_id: int) -> Ejemplar | None:
        return self.ejemplares.get(ejemplar_id)

    obtener_para_modificar = obtener

    def obtener_por_codigo(self, codigo: str) -> Ejemplar | None:
        return next((e for e in self.ejemplares.values() if e.codigo_inventario == codigo), None)

    def listar(self, filtro: FiltroEjemplares, page: int, size: int) -> tuple[list[Ejemplar], int]:
        lista = list(self.ejemplares.values())
        if filtro.sede_id is not None:
            sede = filtro.sede_id
            lista = [e for e in lista if sede in (e.sede_propietaria_id, e.sede_actual_id)]
        if filtro.libro_id is not None:
            lista = [e for e in lista if e.libro_id == filtro.libro_id]
        if filtro.estado is not None:
            lista = [e for e in lista if e.estado_nombre == filtro.estado]
        inicio = (page - 1) * size
        return lista[inicio : inicio + size], len(lista)

    def historial(self, ejemplar_id: int) -> list[MovimientoEjemplar]:
        return list(self.movimientos.get(ejemplar_id, []))

    def contar_de_libro(self, libro_id: int) -> int:
        return sum(1 for e in self.ejemplares.values() if e.libro_id == libro_id)

    def alojados_en_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        lista = [
            e
            for e in self.ejemplares.values()
            if e.sede_actual_id == sede_id and e.estado_nombre != _BAJA
        ]
        return lista[:limite], len(lista)

    def propios_fuera_de_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        lista = [
            e
            for e in self.ejemplares.values()
            if e.sede_propietaria_id == sede_id
            and e.estado_nombre != _BAJA
            and (e.sede_actual_id != sede_id or e.estado_nombre == EstadoEjemplarEnum.EN_TRANSITO)
        ]
        return lista[:limite], len(lista)


class LibroRepositorioEnMemoria:
    """``sedes`` es el repositorio de sedes en memoria (para la disponibilidad por sede activa)."""

    def __init__(self, ejemplares: EjemplarRepositorioEnMemoria, sedes) -> None:  # noqa: ANN001
        self.libros: dict[int, Libro] = {}
        self._ejemplares = ejemplares
        self._sedes = sedes

    def agregar(self, libro: Libro) -> None:
        isbn = libro.datos.isbn.valor if libro.datos.isbn else None
        if self.buscar_duplicado(isbn, libro.datos.clave_natural):
            raise LibroDuplicado("Libro repetido.")
        libro.id = libro.id or max(self.libros, default=0) + 1
        self.libros[libro.id] = libro

    def guardar(self, libro: Libro) -> None:
        assert libro.id in self.libros

    def obtener(self, libro_id: int) -> Libro | None:
        return self.libros.get(libro_id)

    obtener_para_modificar = obtener

    def buscar_duplicado(
        self, isbn: str | None, clave_natural: str | None, excluir_id: int | None = None
    ) -> Libro | None:
        for libro in self.libros.values():
            if libro.id == excluir_id:
                continue
            if isbn and libro.datos.isbn and libro.datos.isbn.valor == isbn:
                return libro
            if not isbn and clave_natural and libro.datos.clave_natural == clave_natural:
                return libro
        return None

    def listar(self, filtro: FiltroLibros, page: int, size: int) -> tuple[list[Libro], int]:
        libros = list(self.libros.values())
        if filtro.categoria_id:
            libros = [lb for lb in libros if lb.datos.categoria.id == filtro.categoria_id]
        if filtro.texto:
            libros = [
                lb
                for lb in libros
                if filtro.texto in normalizar(lb.titulo)
                or any(filtro.texto in normalizar(a) for a in lb.datos.autores)
            ]
        libros.sort(key=lambda lb: normalizar(lb.titulo))
        inicio = (page - 1) * size
        return libros[inicio : inicio + size], len(libros)

    def eliminar(self, libro_id: int) -> None:
        self.libros.pop(libro_id, None)

    def disponibilidad(self, libro_id: int) -> DisponibilidadLibro:
        libro = self.libros[libro_id]
        por_sede: dict[int, list[Ejemplar]] = {}
        for e in self._ejemplares.ejemplares.values():
            sede = self._sedes.sedes.get(e.sede_propietaria_id)
            if e.libro_id != libro_id or e.estado_nombre == _BAJA:
                continue
            if sede is None or sede.estado.value != "ACTIVA":
                continue
            por_sede.setdefault(e.sede_propietaria_id, []).append(e)

        def contar(lista: list[Ejemplar], estado: EstadoEjemplarEnum) -> int:
            return sum(1 for e in lista if e.estado_nombre == estado)

        resultado = []
        for sede_id, lista in sorted(por_sede.items()):
            disp = contar(lista, EstadoEjemplarEnum.DISPONIBLE)
            pres = contar(lista, EstadoEjemplarEnum.PRESTADO)
            res = contar(lista, EstadoEjemplarEnum.RESERVADO)
            tra = contar(lista, EstadoEjemplarEnum.EN_TRANSITO)
            resultado.append(
                DisponibilidadSede(
                    sede_id=sede_id,
                    sede=self._sedes.sedes[sede_id].nombre,
                    totales=len(lista),
                    disponibles=disp,
                    prestados=pres,
                    reservados=res,
                    en_transito=tra,
                    otros=len(lista) - disp - pres - res - tra,
                )
            )
        return DisponibilidadLibro(libro_id, libro.titulo, resultado)
