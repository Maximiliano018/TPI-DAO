"""Entidad ``Sede``: ciclo de vida, edición, excepciones y consulta «abierta ahora»."""

from datetime import date, datetime, time

import pytest

from app.exceptions import (
    ConflictoDeVersion,
    ExcepcionHorarioInvalida,
    ExcepcionHorarioNoEncontrada,
    ExcepcionHorarioSuperpuesta,
    SedeConActividadPendiente,
    SedeEnBaja,
    SedeYaActiva,
    SedeYaEnBaja,
)
from app.models.horario import ExcepcionHorario, TipoExcepcion
from app.models.policies.verificacion_baja_sede import (
    ElementoImpedimento,
    Impedimento,
    TipoImpedimento,
)
from app.models.sede import EstadoSede, Sede, TipoEventoSede
from app.models.valores import CodigoSede, Contacto, Direccion, FranjaHoraria
from tests.factories.sede import ADMIN_REF, CORDOBA, SedeFactory, franjas_tipicas
from tests.fakes.reloj import ZONA, RelojFijo

HOY = date(2026, 11, 10)  # martes
AHORA = RelojFijo().ahora()


def _impedimento(tipo=TipoImpedimento.PRESTAMOS_EN_CURSO, cantidad=2):
    elementos = [ElementoImpedimento(i, f"P-{i}", "ACTIVO") for i in range(1, cantidad + 1)]
    return Impedimento(tipo, cantidad, elementos)


def _nueva(**over) -> Sede:
    datos = {
        "codigo": CodigoSede.crear("CEN"),
        "nombre": "Sede Central",
        "direccion": Direccion.crear("Av. Colón", "1250", CORDOBA),
        "contacto": Contacto.crear("+543514221234", "central@red.example", "Laura Pérez"),
        "horarios": franjas_tipicas(),
        "actor": ADMIN_REF,
        "ahora": AHORA,
    }
    datos.update(over)
    return Sede.crear(**datos)


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-01", "CA-SED-34")
def test_una_sede_nueva_queda_activa_en_version_1_y_registra_el_evento_alta():
    sede = _nueva()

    assert sede.estado == EstadoSede.ACTIVA and sede.version == 1 and sede.baja is None
    [evento] = sede.eventos_pendientes
    assert evento.tipo == TipoEventoSede.ALTA
    assert evento.usuario == ADMIN_REF and evento.fecha_hora == AHORA
    assert evento.estado_nuevo == EstadoSede.ACTIVA
    assert {c.campo for c in evento.cambios} >= {"codigo", "nombre", "telefono", "horarios"}
    assert all(c.antes is None for c in evento.cambios)


@pytest.mark.ca("CA-SED-26")
def test_no_se_puede_crear_una_sede_sin_franjas():
    from app.exceptions import HorarioInvalido

    with pytest.raises(HorarioInvalido):
        _nueva(horarios=[])


# --- modificación ----------------------------------------------------------------------------


def _modificar(sede: Sede, **over) -> bool:
    datos = {
        "nombre": sede.nombre,
        "direccion": sede.direccion,
        "contacto": sede.contacto,
        "horarios": sede.horarios,
        "actor": ADMIN_REF,
        "ahora": AHORA,
    }
    datos.update(over)
    return sede.modificar(**datos)


@pytest.mark.ca("CA-SED-35")
def test_modificar_registra_cada_campo_cambiado_con_su_valor_anterior_y_nuevo():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    cambio = _modificar(
        sede,
        nombre="Sede Central Nueva",
        contacto=Contacto.crear("+543514000000", "central@red.example", "Laura Pérez"),
    )

    assert cambio is True and sede.version == 2 and sede.nombre == "Sede Central Nueva"
    [evento] = sede.eventos_pendientes
    assert evento.tipo == TipoEventoSede.MODIFICACION and evento.version_resultante == 2
    por_campo = {c.campo: c for c in evento.cambios}
    assert set(por_campo) == {"nombre", "telefono"}
    assert por_campo["telefono"].antes == "+543514221234"
    assert por_campo["telefono"].despues == "+543514000000"


def test_modificar_registra_el_cambio_de_horarios_completo():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    _modificar(sede, horarios=[FranjaHoraria(1, time(9), time(18))])

    [cambio] = sede.eventos_pendientes[0].cambios
    assert cambio.campo == "horarios"
    assert cambio.despues == [{"dia_semana": 1, "apertura": "09:00", "cierre": "18:00"}]
    assert len(cambio.antes) == 10


@pytest.mark.ca("CA-SED-27")
def test_los_horarios_se_reemplazan_por_completo():
    sede = _nueva()

    _modificar(sede, horarios=[FranjaHoraria(6, time(10), time(12))])

    assert [(f.dia, f.apertura) for f in sede.horarios] == [(6, time(10))]


def test_modificar_sin_cambios_no_incrementa_la_version_ni_registra_evento():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    assert _modificar(sede) is False
    assert sede.version == 1 and sede.eventos_pendientes == []


def test_modificar_registra_la_confirmacion_de_direccion_duplicada():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    _modificar(
        sede,
        nombre="Otro nombre",
        direccion_duplicada_confirmada=[{"id": 3, "codigo": "NORTE"}],
    )

    campos = [c.campo for c in sede.eventos_pendientes[0].cambios]
    assert "direccion_duplicada_confirmada" in campos


def test_el_codigo_no_cambia_al_modificar():
    sede = _nueva()

    _modificar(sede, nombre="Nuevo nombre")

    assert sede.codigo.valor == "CEN"


@pytest.mark.ca("CA-SED-15")
def test_una_sede_en_baja_rechaza_toda_modificacion():
    sede = SedeFactory(estado=EstadoSede.BAJA)
    excepcion = ExcepcionHorario(fecha=HOY, tipo=TipoExcepcion.CIERRE_TOTAL)

    with pytest.raises(SedeEnBaja):
        _modificar(sede, nombre="Otro")
    with pytest.raises(SedeEnBaja):
        sede.agregar_excepciones([excepcion], actor=ADMIN_REF, ahora=AHORA, hoy=HOY)
    with pytest.raises(SedeEnBaja):
        sede.quitar_excepcion(1, actor=ADMIN_REF, ahora=AHORA, hoy=HOY)


# --- baja y reactivación ---------------------------------------------------------------------


@pytest.mark.ca("CA-SED-08", "CA-SED-36")
def test_la_baja_registra_fecha_motivo_y_usuario_y_el_evento():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    sede.dar_de_baja(motivo="Cierre por obras", actor=ADMIN_REF, ahora=AHORA, impedimentos=[])

    assert sede.estado == EstadoSede.BAJA and sede.version == 2
    assert sede.baja.motivo == "Cierre por obras" and sede.baja.fecha == AHORA
    assert sede.baja.usuario == ADMIN_REF
    [evento] = sede.eventos_pendientes
    assert evento.tipo == TipoEventoSede.BAJA and evento.motivo == "Cierre por obras"
    assert (evento.estado_anterior, evento.estado_nuevo) == (EstadoSede.ACTIVA, EstadoSede.BAJA)


@pytest.mark.ca("CA-SED-07", "CA-SED-23")
def test_con_impedimentos_la_baja_se_rechaza_sin_cambiar_nada_e_informa_el_detalle():
    sede = _nueva()
    sede.eventos_pendientes.clear()
    impedimentos = [
        _impedimento(TipoImpedimento.PRESTAMOS_EN_CURSO, 2),
        _impedimento(TipoImpedimento.BIBLIOTECARIOS_ASIGNADOS, 1),
    ]

    with pytest.raises(SedeConActividadPendiente) as error:
        sede.dar_de_baja(
            motivo="Cierre definitivo", actor=ADMIN_REF, ahora=AHORA, impedimentos=impedimentos
        )

    assert sede.estado == EstadoSede.ACTIVA and sede.baja is None and sede.version == 1
    assert sede.eventos_pendientes == []
    assert "Sede Central" in error.value.mensaje
    assert "actividad pendiente" in error.value.mensaje
    assert "2 préstamos en curso, 1 bibliotecario asignado" in error.value.mensaje
    assert [d["tipo"] for d in error.value.detalles] == [
        "PRESTAMOS_EN_CURSO",
        "BIBLIOTECARIOS_ASIGNADOS",
    ]
    assert (
        error.value.detalles[0]["cantidad"] == 2 and len(error.value.detalles[0]["elementos"]) == 2
    )


@pytest.mark.ca("CA-SED-47")
def test_repetir_la_baja_o_la_reactivacion_informa_que_no_hay_nada_que_hacer():
    activa = _nueva()
    with pytest.raises(SedeYaActiva):
        activa.reactivar(actor=ADMIN_REF, ahora=AHORA)

    activa.dar_de_baja(motivo="Cierre temporal", actor=ADMIN_REF, ahora=AHORA, impedimentos=[])
    with pytest.raises(SedeYaEnBaja):
        activa.dar_de_baja(motivo="Cierre temporal", actor=ADMIN_REF, ahora=AHORA, impedimentos=[])


@pytest.mark.ca("CA-SED-10", "CA-SED-36")
def test_reactivar_vuelve_a_activa_limpia_la_baja_y_registra_el_evento():
    sede = _nueva()
    sede.dar_de_baja(motivo="Cierre por obras", actor=ADMIN_REF, ahora=AHORA, impedimentos=[])
    sede.eventos_pendientes.clear()

    sede.reactivar(actor=ADMIN_REF, ahora=AHORA)

    assert sede.estado == EstadoSede.ACTIVA and sede.baja is None and sede.version == 3
    assert sede.eventos_pendientes[0].tipo == TipoEventoSede.REACTIVACION
    assert sede.horarios == franjas_tipicas()  # los datos vuelven como estaban


@pytest.mark.parametrize("motivo", ["", "    ", "abc", "x" * 301])
def test_el_motivo_de_baja_debe_tener_entre_5_y_300_caracteres(motivo):
    from app.exceptions import ErrorDeValidacion

    sede = _nueva()

    with pytest.raises(ErrorDeValidacion):
        sede.dar_de_baja(motivo=motivo, actor=ADMIN_REF, ahora=AHORA, impedimentos=[])
    assert sede.estado == EstadoSede.ACTIVA


@pytest.mark.ca("CA-SED-09")
def test_validar_operativa_rechaza_una_sede_en_baja_y_acepta_una_activa():
    _nueva().validar_operativa()

    with pytest.raises(SedeEnBaja):
        SedeFactory(estado=EstadoSede.BAJA).validar_operativa()


# --- excepciones de horario ------------------------------------------------------------------


def _agregar(sede, *excepciones):
    sede.agregar_excepciones(list(excepciones), actor=ADMIN_REF, ahora=AHORA, hoy=HOY)


def _cierre(fecha=HOY, **kw):
    return ExcepcionHorario(fecha=fecha, tipo=TipoExcepcion.CIERRE_TOTAL, **kw)


@pytest.mark.ca("CA-SED-32")
def test_no_se_cargan_excepciones_en_fechas_pasadas():
    sede = _nueva()

    with pytest.raises(ExcepcionHorarioInvalida):
        _agregar(sede, _cierre(date(2026, 11, 9)))
    assert sede.excepciones == []


@pytest.mark.ca("CA-SED-31")
def test_una_excepcion_superpuesta_se_rechaza_y_no_agrega_ninguna():
    sede = _nueva()
    _agregar(sede, _cierre(HOY))

    with pytest.raises(ExcepcionHorarioSuperpuesta):
        _agregar(sede, _cierre(date(2026, 11, 11)), _cierre(HOY))
    assert len(sede.excepciones) == 1


def test_las_excepciones_no_incrementan_la_version_pero_registran_evento_y_auditoria():
    sede = _nueva()
    sede.eventos_pendientes.clear()

    _agregar(sede, _cierre(date(2026, 12, 25), motivo="Feriado"))

    assert sede.version == 1
    evento = sede.eventos_pendientes[0]
    assert evento.tipo == TipoEventoSede.EXCEPCION_AGREGADA
    assert evento.cambios[0].despues["motivo"] == "Feriado"


@pytest.mark.ca("CA-SED-33")
def test_se_puede_quitar_una_excepcion_de_hoy_o_futura_pero_no_una_pasada():
    sede = _nueva()
    sede.excepciones = [
        ExcepcionHorario(id=1, fecha=date(2026, 11, 1), tipo=TipoExcepcion.CIERRE_TOTAL),
        ExcepcionHorario(id=2, fecha=HOY, tipo=TipoExcepcion.CIERRE_TOTAL),
    ]
    sede.eventos_pendientes.clear()

    sede.quitar_excepcion(2, actor=ADMIN_REF, ahora=AHORA, hoy=HOY)

    assert [e.id for e in sede.excepciones] == [1]
    assert sede.eventos_pendientes[0].tipo == TipoEventoSede.EXCEPCION_ELIMINADA
    with pytest.raises(ExcepcionHorarioInvalida):
        sede.quitar_excepcion(1, actor=ADMIN_REF, ahora=AHORA, hoy=HOY)
    with pytest.raises(ExcepcionHorarioNoEncontrada):
        sede.quitar_excepcion(99, actor=ADMIN_REF, ahora=AHORA, hoy=HOY)


def test_las_excepciones_vigentes_son_las_de_hoy_y_futuras_ordenadas():
    sede = _nueva()
    sede.excepciones = [
        _cierre(date(2026, 12, 25)),
        _cierre(date(2026, 11, 1)),
        _cierre(HOY),
    ]

    assert [e.fecha for e in sede.excepciones_vigentes(HOY)] == [HOY, date(2026, 12, 25)]


# --- abierta ahora ---------------------------------------------------------------------------


def _local(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, dia, hora, minuto, tzinfo=ZONA)


def test_esta_abierta_segun_el_horario_semanal():
    sede = _nueva()  # lunes a viernes 9-13 y 15-19; 10/11/2026 es martes

    assert sede.esta_abierta(_local(10, 9, 0))
    assert sede.esta_abierta(_local(10, 12, 59))
    assert not sede.esta_abierta(_local(10, 13, 0))  # el cierre no está incluido
    assert not sede.esta_abierta(_local(10, 14, 0))  # entre franjas
    assert sede.esta_abierta(_local(10, 15, 0))
    assert not sede.esta_abierta(_local(14, 10, 0))  # sábado: sin franjas = cerrado


@pytest.mark.ca("CA-SED-29")
def test_un_cierre_total_gana_sobre_el_horario_semanal():
    sede = _nueva()
    _agregar(sede, _cierre(HOY))

    assert not sede.esta_abierta(_local(10, 10, 0))
    assert sede.esta_abierta(_local(11, 10, 0))  # al día siguiente atiende


@pytest.mark.ca("CA-SED-30")
def test_un_cierre_parcial_cierra_solo_su_franja():
    sede = _nueva()
    _agregar(sede, ExcepcionHorario(HOY, TipoExcepcion.CIERRE_PARCIAL, time(10), time(12)))

    assert sede.esta_abierta(_local(10, 9, 30))
    assert not sede.esta_abierta(_local(10, 10, 0))
    assert not sede.esta_abierta(_local(10, 11, 59))
    assert sede.esta_abierta(_local(10, 12, 0))


def test_una_sede_en_baja_nunca_esta_abierta():
    assert not SedeFactory(estado=EstadoSede.BAJA).esta_abierta(_local(10, 10, 0))


def test_el_conflicto_de_version_tiene_su_propio_codigo():
    assert ConflictoDeVersion("x").codigo == "CONFLICTO_DE_VERSION"


def test_cambio_el_domicilio_compara_calle_numero_y_localidad():
    sede = _nueva()

    assert not sede.cambio_el_domicilio(Direccion.crear("Av. Colón", "1250", CORDOBA))
    assert sede.cambio_el_domicilio(Direccion.crear("Av. Colón", "1251", CORDOBA))
