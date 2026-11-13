"""Asignación de ejemplares liberados a la cola de reservas (CU-RES-02).

Cada vez que un ejemplar vuelve a quedar ``Disponible`` (devolución, anulación de un envío,
cancelación de un préstamo, reparación, retorno o una reserva vencida), el caso de uso que lo
liberó llama a ``ColaDeReservas.ofrecer`` dentro de su misma transacción. Así la reasignación es
atómica con la liberación: no queda un ejemplar disponible con socios esperándolo.
"""

from app.exceptions import ReglaDeNegocioViolada
from app.models.ejemplar import Ejemplar
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.reserva import Reserva
from app.models.sede import EstadoSede
from app.models.usuario import UsuarioRef
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj


class ColaDeReservas:
    """Ofrece un ejemplar disponible a la primera reserva elegible de su libro (FIFO)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ofrecer(self, ejemplar: Ejemplar, actor: UsuarioRef | None) -> Reserva | None:
        """Asigna el ejemplar a la primera reserva elegible, si la hay.

        * Socio inhabilitado o dado de baja: se saltea su reserva, que sigue pendiente
          (CA-RES-08).
        * Sede de retiro dada de baja: la reserva se cancela y se pasa a la siguiente.
        * Ejemplar en la sede de retiro: la reserva queda ``Disponible para retiro`` y el ejemplar
          ``Reservado`` (CA-RES-07).
        * Ejemplar en otra sede: se crea el préstamo interbibliotecario hacia la sede de retiro y
          la reserva queda cumplida (CA-RES-09). Si el socio no puede recibir otro préstamo, se
          pasa a la siguiente reserva.

        Returns:
            La reserva que recibió el ejemplar, o ``None`` si nadie lo esperaba.
        """
        if not ejemplar.esta_disponible:
            return None
        assert ejemplar.id is not None
        ahora, hoy = self._reloj.ahora(), self._reloj.hoy()
        parametros = self._uow.parametros.vigentes()
        for reserva in self._uow.reservas.cola_del_libro(ejemplar.libro_id):
            sede_retiro = self._uow.sedes.obtener(reserva.sede_retiro_id)
            if sede_retiro is None or sede_retiro.estado != EstadoSede.ACTIVA:
                reserva.cancelar(ahora)
                self._uow.reservas.guardar(reserva)
                continue
            socio = self._uow.socios.obtener(reserva.socio_id)
            if socio is None or not socio.puede_operar:
                continue
            if ejemplar.sede_actual_id == reserva.sede_retiro_id:
                reserva.asignar(ejemplar.id, hoy, parametros.vigencia_retiro_reserva_dias)
                ejemplar.reservar(actor, ahora, f"Reservado para la reserva {reserva.numero}")
            else:
                sede_origen = self._uow.sedes.obtener(ejemplar.sede_actual_id)
                assert sede_origen is not None
                try:
                    prestamo = PrestamoFactory(parametros).crear(
                        numero=self._uow.prestamos.siguiente_numero(hoy.year),
                        socio=socio,
                        ejemplar=ejemplar,
                        sede_origen=sede_origen,
                        sede_destino=sede_retiro,
                        abiertos_del_socio=self._uow.prestamos.abiertos_de_socio(socio.id or 0),
                        actor=actor,
                        ahora=ahora,
                    )
                except ReglaDeNegocioViolada:
                    continue  # por ejemplo, ya tiene el máximo de préstamos: sigue esperando
                self._uow.prestamos.agregar(prestamo)
                assert prestamo.id is not None
                reserva.convertir_en_prestamo(ejemplar.id, prestamo.id, ahora)
            self._uow.reservas.guardar(reserva)
            self._uow.ejemplares.guardar(ejemplar)
            return reserva
        return None
