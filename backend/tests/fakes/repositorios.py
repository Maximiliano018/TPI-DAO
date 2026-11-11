"""Repositorios y Unit of Work en memoria para las pruebas de dominio y de servicios."""

from app.models.usuario import Usuario
from tests.factories.sede import CORDOBA, RIO_CUARTO


class UsuarioRepositorioEnMemoria:
    """Implementa ``UsuarioRepository`` sin base de datos."""

    def __init__(self, usuarios: list[Usuario] | None = None) -> None:
        self._usuarios: dict[int, Usuario] = {}
        for usuario in usuarios or []:
            self.agregar(usuario)

    def agregar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            usuario.id = max(self._usuarios, default=0) + 1
        self._usuarios[usuario.id] = usuario
        return usuario

    def obtener(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def obtener_por_username(self, username: str) -> Usuario | None:
        return next((u for u in self._usuarios.values() if u.username == username), None)


class UnitOfWorkEnMemoria:
    """Unit of Work con repositorios en memoria; registra si se confirmó."""

    def __init__(self, usuarios: UsuarioRepositorioEnMemoria | None = None) -> None:
        self.usuarios = usuarios or UsuarioRepositorioEnMemoria()
        self.sedes = SedeRepositorioEnMemoria()
        self.localidades = LocalidadRepositorioEnMemoria([CORDOBA, RIO_CUARTO])
        self.confirmaciones = 0
        self.reversiones = 0

    def commit(self) -> None:
        self.confirmaciones += 1

    def rollback(self) -> None:
        self.reversiones += 1


# --- sedes ------------------------------------------------------------------------------------

from dataclasses import replace  # noqa: E402

from app.exceptions import SedeEnBaja, SedeNoEncontrada  # noqa: E402
from app.models.sede import MENSAJE_NO_DISPONIBLE, EstadoSede, EventoSede, Sede  # noqa: E402
from app.models.valores import Localidad  # noqa: E402
from app.repositories.interfaces.sede_repository import (  # noqa: E402
    FiltroEstado,
    FiltroHistorial,
    FiltroSedes,
)
from app.utils.texto import normalizar  # noqa: E402


class SedeRepositorioEnMemoria:
    """Implementa ``SedeRepository`` sin base de datos."""

    def __init__(self) -> None:
        self.sedes: dict[int, Sede] = {}
        self.eventos: dict[int, list[EventoSede]] = {}
        self._ultima_excepcion = 0

    def _persistir_eventos(self, sede: Sede) -> None:
        assert sede.id is not None
        lista = self.eventos.setdefault(sede.id, [])
        for evento in sede.eventos_pendientes:
            evento.id = sum(len(v) for v in self.eventos.values()) + 1
            lista.append(evento)
        sede.eventos_pendientes.clear()

    def _asignar_ids_de_excepciones(self, sede: Sede) -> None:
        for i, excepcion in enumerate(sede.excepciones):
            if excepcion.id is None:
                self._ultima_excepcion += 1
                sede.excepciones[i] = replace(excepcion, id=self._ultima_excepcion)

    def agregar(self, sede: Sede) -> None:
        sede.id = sede.id or max(self.sedes, default=0) + 1
        self.sedes[sede.id] = sede
        self._persistir_eventos(sede)

    def guardar(self, sede: Sede) -> None:
        self._asignar_ids_de_excepciones(sede)
        self._persistir_eventos(sede)

    def obtener(self, sede_id: int) -> Sede | None:
        return self.sedes.get(sede_id)

    obtener_para_modificar = obtener

    def obtener_para_operar(self, sede_id: int) -> Sede:
        sede = self.sedes.get(sede_id)
        if sede is None:
            raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
        if sede.estado != EstadoSede.ACTIVA:
            raise SedeEnBaja(f"La sede {sede.nombre} está dada de baja.")
        return sede

    def buscar_por_codigo(self, codigo: str) -> Sede | None:
        return next((s for s in self.sedes.values() if s.codigo.valor == codigo), None)

    def buscar_por_nombre_normalizado(
        self, nombre_normalizado: str, excluir_id: int | None = None
    ) -> Sede | None:
        return next(
            (
                s
                for s in self.sedes.values()
                if s.nombre_normalizado == nombre_normalizado and s.id != excluir_id
            ),
            None,
        )

    def buscar_por_direccion(
        self, direccion_normalizada: str, excluir_id: int | None = None
    ) -> list[Sede]:
        return [
            s
            for s in self.sedes.values()
            if s.direccion.normalizada() == direccion_normalizada and s.id != excluir_id
        ]

    def listar(self, filtro: FiltroSedes, page: int, size: int) -> tuple[list[Sede], int]:
        sedes = list(self.sedes.values())
        if filtro.estado != FiltroEstado.TODAS:
            sedes = [s for s in sedes if s.estado.value == filtro.estado.value]
        if filtro.localidad_id:
            sedes = [s for s in sedes if s.direccion.localidad.id == filtro.localidad_id]
        if filtro.texto:
            sedes = [
                s
                for s in sedes
                if filtro.texto in s.nombre_normalizado or filtro.texto in s.codigo.valor.lower()
            ]
        clave = filtro.orden.value.lstrip("-")
        sedes.sort(
            key=lambda s: s.nombre_normalizado if clave == "nombre" else s.codigo.valor,
            reverse=filtro.orden.value.startswith("-"),
        )
        inicio = (page - 1) * size
        return sedes[inicio : inicio + size], len(sedes)

    def contar_por_estado(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for sede in self.sedes.values():
            conteo[sede.estado.value] = conteo.get(sede.estado.value, 0) + 1
        return conteo

    def historial(
        self, sede_id: int, filtro: FiltroHistorial, page: int, size: int
    ) -> tuple[list[EventoSede], int]:
        eventos = list(reversed(self.eventos.get(sede_id, [])))
        if filtro.tipo_evento:
            eventos = [e for e in eventos if e.tipo == filtro.tipo_evento]
        inicio = (page - 1) * size
        return eventos[inicio : inicio + size], len(eventos)


class LocalidadRepositorioEnMemoria:
    def __init__(self, localidades: list[Localidad]) -> None:
        self._localidades = {loc.id: loc for loc in localidades}

    def obtener(self, localidad_id: int) -> Localidad | None:
        return self._localidades.get(localidad_id)

    def listar(self, provincia_id: int | None = None, texto: str | None = None) -> list[Localidad]:
        resultado = list(self._localidades.values())
        if provincia_id:
            resultado = [loc for loc in resultado if loc.provincia_id == provincia_id]
        if texto:
            resultado = [loc for loc in resultado if texto in normalizar(loc.nombre)]
        return sorted(resultado, key=lambda loc: loc.nombre)

    def provincias(self) -> list[tuple[int, str]]:
        return sorted({(loc.provincia_id, loc.provincia) for loc in self._localidades.values()})
