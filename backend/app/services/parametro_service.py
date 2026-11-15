"""Consulta, cambio y auditoría de los parámetros de negocio (solo el administrador).

Los parámetros son filas de la tabla ``parametro`` que el administrador edita desde el portal
(Parámetros). Cada cambio queda en ``historial_parametro`` (solo inserción): quién lo hizo,
cuándo, el valor anterior y el nuevo (RF-ACC-07, RF-ACC-12).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from app.exceptions import EntidadNoEncontrada
from app.models.paginacion import Pagina
from app.models.parametros import convertir
from app.models.usuario import Permiso, Usuario, UsuarioRef
from app.models.valores import error_de_campo
from app.repositories.interfaces.prestamo_repository import CambioParametro, Parametro
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj


class ParametroService:
    """Casos de uso de los parámetros (CU-ACC-04)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def listar(self, actor: Usuario) -> list[Parametro]:
        """Los parámetros con su valor vigente y su último cambio."""
        actor.exigir(Permiso.PARAMETROS_ADMINISTRAR)
        return self._uow.parametros.listar()

    def actualizar(self, actor: Usuario, clave: str, valor: str) -> Parametro:
        """Cambia un plazo, límite o monto, que rige desde la siguiente operación, y lo audita.

        Las multas ya emitidas no cambian: guardan el monto vigente al generarse.

        Raises:
            EntidadNoEncontrada: La clave no existe.
            ErrorDeValidacion: Valor no numérico, fuera de rango o igual al vigente.
        """
        actor.exigir(Permiso.PARAMETROS_ADMINISTRAR)
        with self._transaccion():
            actual = self._uow.parametros.obtener_para_modificar(clave)
            if actual is None:
                raise EntidadNoEncontrada(f"No existe el parámetro {clave}.")
            normalizado = str(convertir(clave, valor))
            if str(convertir(clave, actual.valor)) == normalizado:
                raise error_de_campo("valor", "El parámetro ya tiene ese valor.")
            assert actor.id is not None
            parametro = self._uow.parametros.actualizar(
                clave, normalizado, UsuarioRef(actor.id, actor.nombre), self._reloj.ahora()
            )
            assert parametro is not None
        return parametro

    def historial(
        self, actor: Usuario, clave: str | None, page: int, size: int
    ) -> Pagina[CambioParametro]:
        """Auditoría de los cambios, del más reciente al más antiguo."""
        actor.exigir(Permiso.PARAMETROS_ADMINISTRAR)
        cambios, total = self._uow.parametros.historial(clave, page, size)
        return Pagina(cambios, total, page, size)

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()
