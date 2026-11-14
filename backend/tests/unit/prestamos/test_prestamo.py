"""Préstamo: estados (State), plazos (Strategy) y creación (Factory)."""

from datetime import UTC, date, datetime

import pytest

from app.exceptions import (
    EjemplarNoDisponible,
    EjemplarNoPerteneceASede,
    LibroYaPrestado,
    LimitePrestamosExcedido,
    RenovacionNoPermitida,
    SedeEnBaja,
    SocioInhabilitado,
    TransicionInvalida,
)
from app.models.ejemplar import Ejemplar, EstadoFisico
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.parametros import Parametros
from app.models.policies.plazo import PlazoInterbibliotecario, PlazoLocal
from app.models.prestamo import Prestamo, TipoPrestamo
from app.models.sede import EstadoSede, Sede
from app.models.socio import SituacionSocio
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.states.prestamo import EstadoPrestamoEnum as P
from app.models.states.prestamo import estado_prestamo
from app.models.usuario import UsuarioRef
from tests.factories.sede import SedeFactory
from tests.unit.socio.test_socio import socio as nuevo_socio

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
HOY = date(2026, 11, 10)
BIBLIO = UsuarioRef(2, "Biblio")
FABRICA = PrestamoFactory(Parametros())


def sede(sede_id: int, nombre: str) -> Sede:
    return SedeFactory(id=sede_id, nombre=nombre)


def ejemplar(
    sede_id: int = 1, estado: EstadoEjemplarEnum = EstadoEjemplarEnum.DISPONIBLE, libro_id: int = 7
) -> Ejemplar:
    from app.models.states.ejemplar import estado_ejemplar

    nuevo = Ejemplar.registrar(
        codigo_inventario="CEN-1",
        libro_id=libro_id,
        sede_id=sede_id,
        estado_fisico=EstadoFisico.BUENO,
        observaciones=None,
        actor=BIBLIO,
        ahora=AHORA,
    )
    nuevo.id = 11
    nuevo.estado = estado_ejemplar(estado)
    return nuevo


def prestamo(estado: P = P.SOLICITADO, tipo: TipoPrestamo = TipoPrestamo.LOCAL, **over) -> Prestamo:
    valores = {
        "id": 1,
        "numero": "P-2026-000001",
        "tipo": tipo,
        "socio_id": 45,
        "ejemplar_id": 11,
        "libro_id": 7,
        "sede_origen_id": 1,
        "sede_destino_id": 1 if tipo == TipoPrestamo.LOCAL else 2,
        "fecha_solicitud": AHORA,
        "registrado_por": BIBLIO,
        "estado": estado_prestamo(estado),
    }
    valores.update(over)
    return Prestamo(**valores)


# --- plazos (Strategy) -----------------------------------------------------------------------


@pytest.mark.ca("CA-PRE-08", "CA-PRE-09")
def test_cada_politica_calcula_su_vencimiento():
    assert PlazoLocal(14).vencimiento(date(2026, 11, 2)) == date(2026, 11, 16)
    assert PlazoInterbibliotecario(21).vencimiento(date(2026, 11, 2)) == date(2026, 11, 23)
    assert FABRICA.politica(TipoPrestamo.LOCAL).vencimiento(HOY) == date(2026, 11, 24)
    assert FABRICA.politica(TipoPrestamo.INTERBIBLIOTECARIO).vencimiento(HOY) == date(2026, 12, 1)


# --- estados (State) -------------------------------------------------------------------------


@pytest.mark.ca("CA-PRE-08")
def test_entregar_un_local_lo_activa_con_vencimiento_desde_la_entrega():
    p = prestamo()

    p.entregar(HOY, FABRICA.politica(p.tipo), BIBLIO, AHORA)

    assert p.estado_nombre == P.ACTIVO
    assert (p.fecha_inicio, p.fecha_vencimiento) == (HOY, date(2026, 11, 24))


@pytest.mark.ca("CA-PRE-09")
def test_el_interbibliotecario_cuenta_el_plazo_desde_la_entrega_en_destino():
    p = prestamo(P.EN_ENVIO, TipoPrestamo.INTERBIBLIOTECARIO)
    entrega = date(2026, 11, 20)

    p.entregar(entrega, FABRICA.politica(p.tipo), BIBLIO, AHORA)

    assert p.fecha_vencimiento == date(2026, 12, 11)


@pytest.mark.ca("CA-PRE-12")
@pytest.mark.parametrize("final", [P.DEVUELTO, P.CANCELADO])
def test_desde_un_estado_final_no_hay_transiciones(final):
    p = prestamo(final)

    for operacion in (
        lambda: p.entregar(HOY, PlazoLocal(14), BIBLIO, AHORA),
        lambda: p.cancelar("x", BIBLIO, AHORA),
        lambda: p.enviar(BIBLIO, AHORA, "R-1"),
        lambda: p.devolver(AHORA, BIBLIO, AHORA),
    ):
        with pytest.raises(TransicionInvalida):
            operacion()
    assert p.estado_nombre == final


@pytest.mark.ca("CA-PRE-18")
def test_cada_cambio_queda_en_el_historial_con_estado_anterior():
    p = prestamo(P.SOLICITADO, TipoPrestamo.INTERBIBLIOTECARIO)

    p.enviar(BIBLIO, AHORA, "R-2026-000001")
    p.entregar(HOY, PlazoInterbibliotecario(21), BIBLIO, AHORA)

    assert [(m.estado_anterior, m.estado_nuevo) for m in p.movimientos_pendientes] == [
        (P.SOLICITADO, P.EN_ENVIO),
        (P.EN_ENVIO, P.ACTIVO),
    ]
    assert all(m.usuario == BIBLIO and m.fecha_hora == AHORA for m in p.movimientos_pendientes)


@pytest.mark.ca("CA-PRE-13", "CA-PRE-14")
def test_vence_recien_el_dia_siguiente_al_vencimiento():
    p = prestamo(P.ACTIVO, fecha_vencimiento=HOY)

    assert p.marcar_vencido(HOY, AHORA) is False
    assert p.estado_nombre == P.ACTIVO
    assert p.marcar_vencido(date(2026, 11, 11), AHORA) is True
    assert p.estado_nombre == P.VENCIDO
    assert p.dias_de_atraso(date(2026, 11, 15)) == 5


def test_renovar_suma_un_plazo_desde_el_vencimiento_actual():
    p = prestamo(P.ACTIVO, fecha_vencimiento=date(2026, 11, 20))

    p.renovar(HOY, PlazoLocal(14), maximo=1, hay_reservas=False, actor=BIBLIO, ahora=AHORA)

    assert (p.fecha_vencimiento, p.renovaciones) == (date(2026, 12, 4), 1)
    with pytest.raises(RenovacionNoPermitida, match="máximo"):
        p.renovar(HOY, PlazoLocal(14), maximo=1, hay_reservas=False, actor=BIBLIO, ahora=AHORA)


@pytest.mark.ca("CA-PRE-16")
def test_un_prestamo_vencido_no_se_renueva():
    activo_atrasado = prestamo(P.ACTIVO, fecha_vencimiento=date(2026, 11, 9))
    vencido = prestamo(P.VENCIDO, fecha_vencimiento=date(2026, 11, 9))

    with pytest.raises(RenovacionNoPermitida, match="vencido"):
        activo_atrasado.renovar(
            HOY, PlazoLocal(14), maximo=1, hay_reservas=False, actor=BIBLIO, ahora=AHORA
        )
    with pytest.raises(TransicionInvalida):
        vencido.renovar(
            HOY, PlazoLocal(14), maximo=1, hay_reservas=False, actor=BIBLIO, ahora=AHORA
        )


@pytest.mark.ca("CA-PRE-17")
def test_con_reservas_pendientes_no_se_renueva():
    p = prestamo(P.ACTIVO, fecha_vencimiento=date(2026, 11, 20))

    with pytest.raises(RenovacionNoPermitida, match="reservas"):
        p.renovar(HOY, PlazoLocal(14), maximo=1, hay_reservas=True, actor=BIBLIO, ahora=AHORA)


# --- fábrica ---------------------------------------------------------------------------------


def _crear(*, socio=None, ej=None, origen=None, destino=None, abiertos=()):
    origen = origen or sede(1, "Centro")
    return FABRICA.crear(
        numero="P-2026-000009",
        socio=socio or nuevo_socio(),
        ejemplar=ej or ejemplar(),
        sede_origen=origen,
        sede_destino=destino or origen,
        abiertos_del_socio=list(abiertos),
        actor=BIBLIO,
        ahora=AHORA,
    )


@pytest.mark.ca("CA-PRE-10")
def test_la_fabrica_decide_el_tipo_segun_las_sedes_y_aparta_el_ejemplar():
    e = ejemplar()
    local = _crear(ej=e)
    inter = _crear(destino=sede(2, "Norte"))

    assert local.tipo == TipoPrestamo.LOCAL
    assert local.sede_origen_id == local.sede_destino_id == 1
    assert local.estado_nombre == P.SOLICITADO
    assert e.estado_nombre == EstadoEjemplarEnum.APARTADO
    assert inter.tipo == TipoPrestamo.INTERBIBLIOTECARIO
    assert (inter.sede_origen_id, inter.sede_destino_id) == (1, 2)


@pytest.mark.ca("CA-PRE-01", "CA-PRE-07")
@pytest.mark.parametrize(
    "estado",
    [EstadoEjemplarEnum.PRESTADO, EstadoEjemplarEnum.APARTADO, EstadoEjemplarEnum.RESERVADO],
)
def test_no_se_presta_un_ejemplar_que_no_esta_disponible(estado):
    with pytest.raises(EjemplarNoDisponible):
        _crear(ej=ejemplar(estado=estado))


@pytest.mark.ca("CA-PRE-02")
def test_no_se_presta_a_un_socio_inhabilitado():
    s = nuevo_socio()
    s.reevaluar(SituacionSocio(prestamos_vencidos=1), actor=None, ahora=AHORA)

    with pytest.raises(SocioInhabilitado):
        _crear(socio=s)


@pytest.mark.ca("CA-PRE-03")
def test_no_se_presta_un_ejemplar_de_otra_sede_que_la_origen():
    with pytest.raises(EjemplarNoPerteneceASede):
        _crear(ej=ejemplar(sede_id=3))


@pytest.mark.ca("CA-PRE-04", "CA-PRE-05")
def test_no_se_presta_con_una_sede_en_baja():
    en_baja = sede(2, "Norte")
    en_baja.estado = EstadoSede.BAJA

    with pytest.raises(SedeEnBaja):
        _crear(destino=en_baja)
    with pytest.raises(SedeEnBaja):
        _crear(origen=en_baja, ej=ejemplar(sede_id=2))


@pytest.mark.ca("CA-PRE-06", "CA-SOC-08")
def test_un_socio_con_tres_prestamos_no_pide_un_cuarto():
    abiertos = [prestamo(P.ACTIVO, libro_id=i) for i in range(3)]

    with pytest.raises(LimitePrestamosExcedido):
        _crear(abiertos=abiertos)


def test_no_se_presta_dos_veces_el_mismo_libro_al_mismo_socio():
    with pytest.raises(LibroYaPrestado):
        _crear(abiertos=[prestamo(P.ACTIVO, libro_id=7)])


def test_el_alta_queda_en_el_historial():
    p = _crear()

    [mov] = p.movimientos_pendientes
    assert (mov.estado_anterior, mov.estado_nuevo) == (None, P.SOLICITADO)


# --- plazo de retiro y cancelación del socio ------------------------------------------------


@pytest.mark.ca("CA-PRE-25")
def test_un_local_registrado_con_fecha_queda_con_plazo_de_retiro():
    local = FABRICA.crear(
        numero="P-2026-000010",
        socio=nuevo_socio(),
        ejemplar=ejemplar(),
        sede_origen=sede(1, "Centro"),
        sede_destino=sede(1, "Centro"),
        abiertos_del_socio=[],
        actor=BIBLIO,
        ahora=AHORA,
        hoy=HOY,
    )
    inter = FABRICA.crear(
        numero="P-2026-000011",
        socio=nuevo_socio(),
        ejemplar=ejemplar(),
        sede_origen=sede(1, "Centro"),
        sede_destino=sede(2, "Norte"),
        abiertos_del_socio=[],
        actor=BIBLIO,
        ahora=AHORA,
        hoy=HOY,
    )

    assert local.fecha_limite_retiro == date(2026, 11, 13)
    assert inter.fecha_limite_retiro is None  # empieza cuando llega a destino


@pytest.mark.ca("CA-PRE-25", "CA-PRE-26")
def test_el_retiro_vence_el_dia_siguiente_al_limite_y_solo_sin_entregar():
    p = prestamo(P.EN_ENVIO, TipoPrestamo.INTERBIBLIOTECARIO)
    assert not p.retiro_vencido(date(2026, 12, 1))  # todavía en camino: sin plazo

    p.habilitar_retiro(date(2026, 11, 13), BIBLIO, AHORA)

    assert (p.estado_nombre, p.fecha_limite_retiro) == (P.EN_ENVIO, date(2026, 11, 13))
    assert p.movimientos_pendientes[-1].observacion == "Disponible para retirar hasta el 13/11/2026"
    assert not p.retiro_vencido(date(2026, 11, 13))
    assert p.retiro_vencido(date(2026, 11, 14))
    entregado = prestamo(P.ACTIVO, fecha_limite_retiro=date(2026, 11, 1))
    assert not entregado.retiro_vencido(date(2026, 11, 14))


@pytest.mark.ca("CA-PRE-27")
@pytest.mark.parametrize(
    ("estado", "cancelable"), [(P.SOLICITADO, True), (P.EN_ENVIO, False), (P.ACTIVO, False)]
)
def test_el_socio_solo_cancela_lo_que_todavia_no_salio(estado, cancelable):
    assert prestamo(estado).cancelable_por_el_socio is cancelable


@pytest.mark.ca("CA-PRE-23")
def test_las_reglas_del_socio_se_controlan_sin_ejemplar():
    socio = nuevo_socio()
    abierto = prestamo(P.ACTIVO, libro_id=7)

    with pytest.raises(LibroYaPrestado):
        FABRICA.validar_socio(socio, [abierto], libro_id=7)
    with pytest.raises(LimitePrestamosExcedido):
        FABRICA.validar_socio(socio, [abierto] * 3, libro_id=8)
    FABRICA.validar_socio(socio, [abierto], libro_id=8)
