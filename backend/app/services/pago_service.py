"""Casos de uso del pago de multas: en el mostrador o en línea (simulado).

Reglas (RF-DEV-17 a 20):

* El bibliotecario cobra en el mostrador e indica el medio (efectivo, débito, crédito o
  transferencia); la multa queda saldada en el acto y se cancela el pago en línea en curso.
* El socio paga en línea solo sus multas pendientes. Es una simulación para la demo: el pago
  queda pendiente y en el checkout simulado el socio elige la forma de pago y confirma. Aprobado,
  la multa queda saldada y se reevalúa al socio; rechazado (tarjeta de prueba terminada en 0002),
  la multa sigue pendiente y puede reintentar. No hay cobro real ni pasarela externa.
* Todo pago aprobado tiene su comprobante en PDF (RF-DEV-22).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from app.exceptions import MultaNoEncontrada, PagoNoEncontrado, TransicionInvalida
from app.models.devolucion import Multa
from app.models.pago import EstadoPago, FormaEnLinea, MedioPago, Pago
from app.models.usuario import Permiso, Usuario, UsuarioRef
from app.repositories.unit_of_work import UnitOfWork
from app.services.comprobante_pago import comprobante_pdf, nombre_de_archivo
from app.services.situacion_socio import reevaluar_socio
from app.utils.reloj import Reloj


class PagoService:
    """Pagos de multas (extensión del proceso 8)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- mostrador ------------------------------------------------------------------------

    def saldar_en_mostrador(
        self, actor: Usuario, multa_id: int, medio: MedioPago, comprobante: str | None
    ) -> Multa:
        """El bibliotecario cobró: registra el pago y salda la multa (CU-DEV-05, CA-DEV-21).

        Raises:
            MultaNoEncontrada; TransicionInvalida: ya estaba saldada.
            ErrorDeValidacion: medio que no es de mostrador o comprobante muy largo.
        """
        actor.exigir(Permiso.MULTA_SALDAR)
        with self._transaccion():
            multa = self._multa_para_modificar(multa_id)
            self._exigir_pendiente(multa)
            ahora, yo = self._reloj.ahora(), _ref(actor)
            pago = Pago.manual(
                multa_id=multa_id,
                monto=multa.monto_total,
                medio=medio,
                comprobante=comprobante,
                actor=yo,
                ahora=ahora,
            )
            en_curso = self._uow.pagos.pendiente_de_multa(multa_id)
            if en_curso is not None:
                en_curso.cancelar("Se cobró en el mostrador")
                self._uow.pagos.guardar(en_curso)
            self._uow.pagos.agregar(pago)
            self._saldar(multa, yo, ahora)
        return self._uow.multas.obtener(multa_id) or multa

    # --- en línea (simulado) --------------------------------------------------------------

    def iniciar_en_linea(self, actor: Usuario, multa_id: int) -> Pago:
        """El socio inicia el pago de su multa; si ya tenía uno en curso, lo retoma (CA-DEV-22).

        Raises:
            MultaNoEncontrada: no existe o es de otro socio (no se revela).
            TransicionInvalida: ya está saldada.
        """
        actor.exigir(Permiso.MULTA_PAGAR_PROPIA)
        with self._transaccion():
            multa = self._uow.multas.obtener_para_modificar(multa_id)
            if multa is None or actor.socio_id is None or multa.socio_id != actor.socio_id:
                raise MultaNoEncontrada("La multa solicitada no existe.")
            self._exigir_pendiente(multa)
            en_curso = self._uow.pagos.pendiente_de_multa(multa_id)
            if en_curso is not None:
                return en_curso
            pago = Pago.en_linea(
                multa_id=multa_id,
                monto=multa.monto_total,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            self._uow.pagos.agregar(pago)
        return pago

    def pagar_en_linea(
        self, actor: Usuario, pago_id: int, forma: FormaEnLinea, tarjeta_ultimos4: str | None
    ) -> Pago:
        """El socio confirma el pago en el checkout simulado (CA-DEV-23, 24, 28).

        De la tarjeta solo llegan los últimos 4 dígitos. Aprobado: la multa queda saldada y el
        socio se reevalúa. Rechazado: la multa sigue pendiente y puede iniciar otro pago.

        Raises:
            PagoNoEncontrado: no existe o no es de una multa del socio.
            ErrorDeValidacion: tarjeta sin sus últimos 4 dígitos (o dígitos con dinero en cuenta).
            TransicionInvalida: el pago ya no está pendiente (por ejemplo, se cobró en el
                mostrador mientras tanto).
        """
        actor.exigir(Permiso.MULTA_PAGAR_PROPIA)
        with self._transaccion():
            visto = self._uow.pagos.obtener(pago_id)
            if visto is None or not self._es_del_socio(actor, visto):
                raise PagoNoEncontrado("El pago solicitado no existe.")
            # Mismo orden de bloqueo que el cobro en el mostrador (multa y después pago), para
            # que un pago en línea y un cobro simultáneos se esperen en lugar de trabarse.
            multa = self._multa_para_modificar(visto.multa_id)
            pago = self._uow.pagos.obtener_para_modificar(pago_id)
            assert pago is not None
            ahora = self._reloj.ahora()
            aprobado = pago.pagar_en_linea(forma, tarjeta_ultimos4, ahora)
            self._uow.pagos.guardar(pago)
            if aprobado:
                self._saldar(multa, None, ahora)
        return self._uow.pagos.obtener(pago_id) or pago

    def comprobante(self, actor: Usuario, pago_id: int) -> tuple[str, bytes]:
        """Comprobante en PDF de un pago aprobado: nombre del archivo y contenido (CA-DEV-27).

        Raises:
            PagoNoEncontrado: no existe o es de otro socio.
            TransicionInvalida: el pago no está aprobado.
        """
        pago = self.detalle(actor, pago_id)
        if pago.estado != EstadoPago.APROBADO:
            raise TransicionInvalida(
                "Solo un pago aprobado tiene comprobante.",
                [{"campo": "estado", "problema": pago.estado.value}],
            )
        zona = self._reloj.ahora_local().tzinfo
        assert zona is not None
        return nombre_de_archivo(pago), comprobante_pdf(pago, zona)

    def detalle(self, actor: Usuario, pago_id: int) -> Pago:
        """El pago: el personal ve cualquiera; el socio, solo los de sus multas."""
        pago = self._uow.pagos.obtener(pago_id)
        if pago is None or not (actor.puede(Permiso.MULTA_LEER) or self._es_del_socio(actor, pago)):
            raise PagoNoEncontrado("El pago solicitado no existe.")
        return pago

    # --- internos -------------------------------------------------------------------------

    def _saldar(self, multa: Multa, actor: UsuarioRef | None, ahora: datetime) -> None:
        multa.saldar(actor, ahora)
        self._uow.multas.guardar(multa)
        origen = f"Multa del préstamo {multa.numero_prestamo or multa.prestamo_id} saldada"
        reevaluar_socio(self._uow, multa.socio_id, actor, ahora, origen)

    def _multa_para_modificar(self, multa_id: int) -> Multa:
        multa = self._uow.multas.obtener_para_modificar(multa_id)
        if multa is None:
            raise MultaNoEncontrada("La multa solicitada no existe.")
        return multa

    @staticmethod
    def _exigir_pendiente(multa: Multa) -> None:
        if not multa.pendiente:
            raise TransicionInvalida(
                "La multa ya está saldada.", [{"campo": "estado", "problema": "SALDADA"}]
            )

    def _es_del_socio(self, actor: Usuario, pago: Pago) -> bool:
        if not actor.puede(Permiso.MULTA_PAGAR_PROPIA) or actor.socio_id is None:
            return False
        multa = self._uow.multas.obtener(pago.multa_id)
        return multa is not None and multa.socio_id == actor.socio_id

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
