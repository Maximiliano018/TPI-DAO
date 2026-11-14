"""Asignación de ejemplares a la cola de reservas (CU-RES-02).

Cada vez que un ejemplar queda ``Disponible`` (alta, devolución, anulación de un envío,
cancelación de un préstamo, reparación, recuperación, retorno o una reserva vencida o
cancelada), el caso de uso que lo dejó así llama a ``ColaDeReservas.ofrecer`` dentro de su misma
transacción. Así la asignación es atómica: no queda un ejemplar disponible con socios
esperándolo.

Todo lo que hace la cola lo hace **el sistema** (autor ``None``), aunque la haya disparado un
bibliotecario o un socio: la asignación, el préstamo entre sedes que genera y las cancelaciones
automáticas (RF-RES-14).
"""

from app.exceptions import ReglaDeNegocioViolada
from app.models.ejemplar import Ejemplar
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.reserva import Reserva
from app.models.sede import EstadoSede
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj

MOTIVO_SIN_EJEMPLARES = "El libro ya no tiene ejemplares en la red"


class ColaDeReservas:
    """Ofrece un ejemplar disponible a la primera reserva elegible de su libro (FIFO)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ofrecer(self, ejemplar: Ejemplar) -> Reserva | None:
        """Asigna el ejemplar a la primera reserva elegible, si la hay.

        * Socio inhabilitado o dado de baja: se saltea su reserva, que sigue pendiente
          (CA-RES-08).
        * Socio que no puede recibir otro préstamo (máximo alcanzado o el mismo libro en curso):
          también se saltea y sigue esperando (CA-RES-20).
        * Sede de retiro dada de baja: la reserva se cancela y se pasa a la siguiente.
        * Ejemplar en la sede de retiro: la reserva queda ``Disponible para retiro`` y el ejemplar
          ``Reservado`` (CA-RES-07).
        * Ejemplar en otra sede: se crea el préstamo interbibliotecario hacia la sede de retiro y
          la reserva queda cumplida (CA-RES-09).

        Returns:
            La reserva que recibió el ejemplar, o ``None`` si nadie lo esperaba.
        """
        if not ejemplar.esta_disponible:
            return None
        assert ejemplar.id is not None
        ahora, hoy = self._reloj.ahora(), self._reloj.hoy()
        parametros = self._uow.parametros.vigentes()
        fabrica = PrestamoFactory(parametros)
        for reserva in self._uow.reservas.cola_del_libro(ejemplar.libro_id):
            sede_retiro = self._uow.sedes.obtener(reserva.sede_retiro_id)
            if sede_retiro is None or sede_retiro.estado != EstadoSede.ACTIVA:
                reserva.cancelar(ahora, None, "La sede de retiro fue dada de baja")
                self._uow.reservas.guardar(reserva)
                continue
            socio = self._uow.socios.obtener(reserva.socio_id)
            if socio is None or not socio.puede_operar:
                continue
            abiertos = self._uow.prestamos.abiertos_de_socio(reserva.socio_id)
            if ejemplar.sede_actual_id == reserva.sede_retiro_id:
                try:
                    fabrica.validar_socio(socio, abiertos, ejemplar.libro_id)
                except ReglaDeNegocioViolada:
                    continue  # no podría retirarlo: el ejemplar no se le retiene
                reserva.asignar(
                    ejemplar.id,
                    hoy,
                    parametros.vigencia_retiro_reserva_dias,
                    ahora,
                    ejemplar.codigo_inventario,
                )
                ejemplar.reservar(None, ahora, f"Reservado para la reserva {reserva.numero}")
            else:
                sede_origen = self._uow.sedes.obtener(ejemplar.sede_actual_id)
                assert sede_origen is not None
                try:
                    prestamo = fabrica.crear(
                        numero=self._uow.prestamos.siguiente_numero(hoy.year),
                        socio=socio,
                        ejemplar=ejemplar,
                        sede_origen=sede_origen,
                        sede_destino=sede_retiro,
                        abiertos_del_socio=abiertos,
                        actor=None,
                        ahora=ahora,
                    )
                except ReglaDeNegocioViolada:
                    continue  # por ejemplo, ya tiene el máximo de préstamos: sigue esperando
                self._uow.prestamos.agregar(prestamo)
                assert prestamo.id is not None
                reserva.convertir_en_prestamo(ejemplar.id, prestamo.id, ahora, prestamo.numero)
            self._uow.reservas.guardar(reserva)
            self._uow.ejemplares.guardar(ejemplar)
            return reserva
        return None

    def revisar_libro(self, libro_id: int) -> int:
        """Cancela las reservas pendientes de un libro que se quedó sin ejemplares (RF-RES-17).

        Se llama después de dar de baja un ejemplar. Si queda algún ejemplar activo en la red, o
        un extravío sin resolver (el ejemplar puede aparecer y recuperarse), las reservas siguen
        esperando.

        Returns:
            Cuántas reservas se cancelaron.
        """
        if self._uow.ejemplares.activos_de_libro(libro_id) > 0:
            return 0
        if self._uow.incidencias.hay_extravio_pendiente_de_libro(libro_id):
            return 0
        ahora = self._reloj.ahora()
        canceladas = 0
        for reserva in self._uow.reservas.cola_del_libro(libro_id):
            reserva.cancelar(ahora, None, MOTIVO_SIN_EJEMPLARES)
            self._uow.reservas.guardar(reserva)
            canceladas += 1
        return canceladas
