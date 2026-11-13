"""Consulta y cambio de los parámetros de negocio (solo el administrador)."""

from app.exceptions import EntidadNoEncontrada
from app.models.parametros import convertir
from app.models.usuario import Permiso, Usuario
from app.repositories.interfaces.prestamo_repository import Parametro
from app.repositories.unit_of_work import UnitOfWork


class ParametroService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def listar(self, actor: Usuario) -> list[Parametro]:
        actor.exigir(Permiso.PARAMETROS_ADMINISTRAR)
        return self._uow.parametros.listar()

    def actualizar(self, actor: Usuario, clave: str, valor: str) -> Parametro:
        """Cambia un plazo, límite o monto; rige desde la siguiente operación.

        Las multas ya emitidas no cambian: guardan el monto por día vigente al generarse.

        Raises:
            ErrorDeValidacion: Valor no numérico o fuera de rango.
            EntidadNoEncontrada: La clave no existe.
        """
        actor.exigir(Permiso.PARAMETROS_ADMINISTRAR)
        if clave not in [p.clave for p in self._uow.parametros.listar()]:
            raise EntidadNoEncontrada(f"No existe el parámetro {clave}.")
        normalizado = str(convertir(clave, valor))
        try:
            parametro = self._uow.parametros.actualizar(clave, normalizado)
            assert parametro is not None
            self._uow.commit()
        except BaseException:
            self._uow.rollback()
            raise
        return parametro
