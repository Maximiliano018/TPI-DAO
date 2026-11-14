"""Reglas del socio: documento, datos, inhabilitación, baja y reactivación."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from app.exceptions import (
    ErrorDeValidacion,
    PermisoDenegado,
    SinSolicitudPendiente,
    SocioConActividadPendiente,
    SocioConCausasVigentes,
    SocioEnBaja,
    SocioInhabilitado,
    SocioNoReactivable,
    SocioYaActivo,
    SocioYaEnBaja,
    SocioYaHabilitado,
    SocioYaInhabilitado,
    SolicitudYaPendiente,
)
from app.models.socio import (
    DatosPersonales,
    Documento,
    EstadoSocio,
    MotivoInhabilitacion,
    SituacionSocio,
    Socio,
    TipoBaja,
    TipoDocumento,
    TipoEventoSocio,
    formatear_numero_socio,
)
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
A_PEDIDO = TipoBaja.A_PEDIDO
MOSTRADOR = "Reactivación en mostrador"
HOY = date(2026, 11, 10)
ADMIN = UsuarioRef(1, "Admin")
SIN_NADA = SituacionSocio()
CON_VENCIDO = SituacionSocio(prestamos_activos=0, prestamos_vencidos=1)
CON_MULTA = SituacionSocio(multas_pendientes=1)
CON_AMBOS = SituacionSocio(prestamos_vencidos=1, multas_pendientes=1)


def datos(**over) -> DatosPersonales:
    valores = {
        "documento": Documento.crear(TipoDocumento.DNI, "30111222"),
        "nombre": "Lucía",
        "apellido": "Gómez",
        "fecha_nacimiento": date(1995, 4, 12),
        "email": "lucia@example.com",
        "telefono": None,
        "domicilio": "San Martín 123",
        "hoy": HOY,
    }
    valores.update(over)
    return DatosPersonales.crear(**valores)


def socio(**over) -> Socio:
    nuevo = Socio.registrar(
        numero_socio="00045", datos=datos(), sede_alta_id=1, actor=ADMIN, ahora=AHORA
    )
    nuevo.id = 45
    for clave, valor in over.items():
        setattr(nuevo, clave, valor)
    return nuevo


# --- documento y datos -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tipo", "texto", "esperado"),
    [
        (TipoDocumento.DNI, "30.111.222", "30111222"),
        (TipoDocumento.DNI, " 7123456 ", "7123456"),
        (TipoDocumento.LC, "1234567", "1234567"),
        (TipoDocumento.PASAPORTE, "aab-123456", "AAB123456"),
    ],
)
def test_el_documento_se_normaliza(tipo, texto, esperado):
    assert Documento.crear(tipo, texto).numero == esperado


@pytest.mark.parametrize(
    ("tipo", "texto"),
    [
        (TipoDocumento.DNI, "123456"),
        (TipoDocumento.DNI, "301112223"),
        (TipoDocumento.DNI, "30A11222"),
        (TipoDocumento.PASAPORTE, "AB12"),
        (TipoDocumento.DNI, ""),
    ],
)
def test_un_documento_con_formato_invalido_se_rechaza(tipo, texto):
    with pytest.raises(ErrorDeValidacion) as error:
        Documento.crear(tipo, texto)
    assert error.value.detalles[0]["campo"] == "nro_documento"


def test_los_datos_validos_quedan_normalizados():
    d = datos(nombre="  Lucía  ", email="Lucia@Example.com", telefono="+54 351 500-0000")

    assert d.nombre == "Lucía" and d.email.valor == "lucia@example.com"
    assert d.telefono.valor == "+543515000000" and d.nombre_completo == "Lucía Gómez"


@pytest.mark.parametrize(
    ("over", "campo"),
    [
        ({"nombre": "  "}, "nombre"),
        ({"apellido": ""}, "apellido"),
        ({"email": None, "telefono": None}, "email"),
        ({"email": "no-es-correo"}, "email"),
        ({"telefono": "123"}, "telefono"),
        ({"fecha_nacimiento": date(2026, 11, 11)}, "fecha_nacimiento"),
        ({"fecha_nacimiento": date(1899, 12, 31)}, "fecha_nacimiento"),
        ({"domicilio": "x" * 201}, "domicilio"),
    ],
)
def test_datos_obligatorios_o_con_formato_invalido_se_rechazan(over, campo):
    with pytest.raises(ErrorDeValidacion) as error:
        datos(**over)
    assert error.value.detalles[0]["campo"] == campo


def test_el_numero_de_socio_tiene_cinco_digitos():
    assert formatear_numero_socio(45) == "00045"
    assert formatear_numero_socio(123456) == "123456"


# --- alta y modificación ---------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-01")
def test_un_socio_nuevo_queda_habilitado_sin_causas():
    nuevo = socio()

    assert nuevo.estado == EstadoSocio.HABILITADO and nuevo.causas == set()
    assert nuevo.motivo_inhabilitacion is None and nuevo.puede_operar
    assert (nuevo.fecha_alta, nuevo.creado_por) == (AHORA, ADMIN)


def test_modificar_reemplaza_los_datos_y_avisa_si_no_cambio_nada():
    s = socio()

    assert s.modificar(datos(), actor=ADMIN, ahora=AHORA) is False
    assert s.modificar(datos(apellido="Pérez"), actor=ADMIN, ahora=AHORA) is True
    assert s.datos.apellido == "Pérez"


def test_un_socio_en_baja_no_se_modifica():
    s = socio()
    s.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
    )

    with pytest.raises(SocioEnBaja):
        s.modificar(datos(apellido="Pérez"), actor=ADMIN, ahora=AHORA)


# --- inhabilitación automática ---------------------------------------------------------------


@pytest.mark.ca("CA-SOC-05")
def test_un_prestamo_vencido_inhabilita_al_socio():
    s = socio()

    assert s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA) is True
    assert s.estado == EstadoSocio.INHABILITADO
    assert s.motivo_inhabilitacion == MotivoInhabilitacion.PRESTAMO_VENCIDO


@pytest.mark.ca("CA-SOC-06")
def test_con_vencido_y_multa_devolver_no_alcanza_si_la_multa_sigue_pendiente():
    s = socio()
    s.reevaluar(CON_AMBOS, actor=None, ahora=AHORA)

    s.reevaluar(CON_MULTA, actor=None, ahora=AHORA)

    assert s.estado == EstadoSocio.INHABILITADO
    assert s.causas == {MotivoInhabilitacion.MULTA_IMPAGA}


@pytest.mark.ca("CA-SOC-07")
def test_sin_causas_vigentes_vuelve_a_quedar_habilitado():
    s = socio()
    s.reevaluar(CON_AMBOS, actor=None, ahora=AHORA)

    s.reevaluar(SIN_NADA, actor=None, ahora=AHORA)

    assert s.estado == EstadoSocio.HABILITADO and s.motivo_inhabilitacion is None


def test_reevaluar_sin_cambios_no_toca_al_socio():
    s = socio()

    assert s.reevaluar(SIN_NADA, actor=None, ahora=AHORA) is False


# --- inhabilitación administrativa -----------------------------------------------------------


def test_la_inhabilitacion_administrativa_tiene_prioridad_y_conserva_las_automaticas():
    s = socio()
    s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA)

    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)

    assert s.motivo_inhabilitacion == MotivoInhabilitacion.ADMINISTRATIVA
    assert s.causas == {MotivoInhabilitacion.ADMINISTRATIVA, MotivoInhabilitacion.PRESTAMO_VENCIDO}
    assert s.motivo_administrativo == "Daño reiterado de material"


def test_reevaluar_no_levanta_la_causa_administrativa():
    s = socio()
    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)

    s.reevaluar(SIN_NADA, actor=None, ahora=AHORA)

    assert s.estado == EstadoSocio.INHABILITADO
    assert s.motivo_inhabilitacion == MotivoInhabilitacion.ADMINISTRATIVA


@pytest.mark.parametrize("motivo", ["", "abc", "x" * 301])
def test_la_inhabilitacion_exige_un_motivo_valido(motivo):
    with pytest.raises(ErrorDeValidacion):
        socio().inhabilitar(motivo, actor=ADMIN, ahora=AHORA)


def test_no_se_inhabilita_dos_veces_por_decision_administrativa():
    s = socio()
    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)

    with pytest.raises(SocioYaInhabilitado):
        s.inhabilitar("Otro motivo cualquiera", actor=ADMIN, ahora=AHORA)


@pytest.mark.ca("CA-SOC-10")
def test_un_bibliotecario_no_levanta_una_inhabilitacion_administrativa():
    s = socio()
    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)

    with pytest.raises(PermisoDenegado):
        s.rehabilitar(SIN_NADA, actor=UsuarioRef(2, "Biblio"), es_administrador=False, ahora=AHORA)
    assert s.estado == EstadoSocio.INHABILITADO


def test_el_administrador_levanta_la_administrativa_y_queda_la_automatica():
    s = socio()
    s.reevaluar(CON_MULTA, actor=None, ahora=AHORA)
    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)

    s.rehabilitar(CON_MULTA, actor=ADMIN, es_administrador=True, ahora=AHORA)

    assert s.motivo_administrativo is None
    assert s.estado == EstadoSocio.INHABILITADO
    assert s.motivo_inhabilitacion == MotivoInhabilitacion.MULTA_IMPAGA


def test_rehabilitar_con_causas_automaticas_vigentes_se_rechaza():
    s = socio()
    s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA)

    with pytest.raises(SocioConCausasVigentes) as error:
        s.rehabilitar(CON_VENCIDO, actor=ADMIN, es_administrador=True, ahora=AHORA)
    assert error.value.detalles == [{"campo": "causas", "problema": "PRESTAMO_VENCIDO"}]


def test_rehabilitar_corrige_un_estado_sin_causas_y_rechaza_si_ya_estaba_habilitado():
    s = socio()
    s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA)

    s.rehabilitar(SIN_NADA, actor=ADMIN, es_administrador=False, ahora=AHORA)

    assert s.estado == EstadoSocio.HABILITADO
    with pytest.raises(SocioYaHabilitado):
        s.rehabilitar(SIN_NADA, actor=ADMIN, es_administrador=False, ahora=AHORA)


@pytest.mark.ca("CA-SOC-04")
def test_un_socio_inhabilitado_o_en_baja_no_puede_operar():
    inhabilitado = socio()
    inhabilitado.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA)
    en_baja = socio()
    en_baja.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
    )

    with pytest.raises(SocioInhabilitado) as error:
        inhabilitado.validar_puede_operar()
    assert "préstamo vencido" in error.value.mensaje
    with pytest.raises(SocioEnBaja):
        en_baja.validar_puede_operar()
    socio().validar_puede_operar()


# --- baja y reactivación ---------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-09")
@pytest.mark.parametrize(
    ("situacion", "tipos"),
    [
        (SituacionSocio(prestamos_activos=1), ["PRESTAMOS_EN_CURSO"]),
        (SituacionSocio(prestamos_vencidos=2), ["PRESTAMOS_EN_CURSO"]),
        (SituacionSocio(multas_pendientes=1), ["MULTAS_PENDIENTES"]),
        (
            SituacionSocio(prestamos_activos=1, multas_pendientes=1),
            ["PRESTAMOS_EN_CURSO", "MULTAS_PENDIENTES"],
        ),
    ],
)
def test_la_baja_se_bloquea_con_prestamos_en_curso_o_multas(situacion, tipos):
    s = socio()

    with pytest.raises(SocioConActividadPendiente) as error:
        s.dar_de_baja(
            situacion,
            A_PEDIDO,
            "Se mudó de ciudad",
            actor=ADMIN,
            es_administrador=True,
            ahora=AHORA,
        )
    assert [d["tipo"] for d in error.value.detalles] == tipos
    assert s.estado == EstadoSocio.HABILITADO


def test_la_baja_registra_tipo_y_motivo():
    s = socio()

    s.dar_de_baja(
        SituacionSocio(reservas_activas=2),
        A_PEDIDO,
        "Se mudó de ciudad",
        actor=ADMIN,
        es_administrador=True,
        ahora=AHORA,
    )

    assert s.estado == EstadoSocio.BAJA and s.causas == set()
    assert (s.tipo_baja, s.fecha_baja, s.motivo_baja) == (A_PEDIDO, AHORA, "Se mudó de ciudad")
    with pytest.raises(SocioYaEnBaja):
        s.dar_de_baja(
            SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
        )


def test_reactivar_vuelve_a_habilitar_y_solo_aplica_a_socios_en_baja():
    s = socio()
    with pytest.raises(SocioYaActivo):
        s.reactivar(actor=ADMIN, es_administrador=True, ahora=AHORA, origen=MOSTRADOR)
    s.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
    )

    s.reactivar(actor=ADMIN, es_administrador=True, ahora=AHORA, origen=MOSTRADOR)

    assert s.estado == EstadoSocio.HABILITADO
    assert (s.fecha_baja, s.motivo_baja) == (None, None)


def test_un_socio_en_baja_no_se_reevalua_ni_se_inhabilita():
    s = socio()
    s.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
    )

    assert s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA) is False
    with pytest.raises(SocioEnBaja):
        s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)
    with pytest.raises(SocioEnBaja):
        s.rehabilitar(SIN_NADA, actor=ADMIN, es_administrador=True, ahora=AHORA)


# --- tipos de baja, reactivación y solicitud ---------------------------------------------------

BIBLIO = UsuarioRef(2, "Bibliotecaria")
SOCIA = UsuarioRef(3, "Lucía Gómez")


def _de_baja(tipo: TipoBaja = A_PEDIDO) -> Socio:
    s = socio()
    s.dar_de_baja(
        SIN_NADA, tipo, "Motivo de la baja", actor=ADMIN, es_administrador=True, ahora=AHORA
    )
    return s


@pytest.mark.ca("CA-SOC-12")
def test_el_bibliotecario_solo_registra_la_baja_a_pedido_del_socio():
    for tipo in (TipoBaja.ADMINISTRATIVA, TipoBaja.FALLECIMIENTO):
        with pytest.raises(PermisoDenegado):
            socio().dar_de_baja(
                SIN_NADA,
                tipo,
                "Motivo de la baja",
                actor=BIBLIO,
                es_administrador=False,
                ahora=AHORA,
            )

    s = socio()
    s.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=BIBLIO, es_administrador=False, ahora=AHORA
    )
    assert s.estado == EstadoSocio.BAJA


@pytest.mark.ca("CA-SOC-12", "CA-SOC-13")
def test_quien_reactiva_depende_del_tipo_de_baja():
    _de_baja(A_PEDIDO).reactivar(
        actor=BIBLIO, es_administrador=False, ahora=AHORA, origen=MOSTRADOR
    )
    with pytest.raises(PermisoDenegado):
        _de_baja(TipoBaja.ADMINISTRATIVA).reactivar(
            actor=BIBLIO, es_administrador=False, ahora=AHORA, origen=MOSTRADOR
        )
    _de_baja(TipoBaja.ADMINISTRATIVA).reactivar(
        actor=ADMIN, es_administrador=True, ahora=AHORA, origen=MOSTRADOR
    )
    with pytest.raises(SocioNoReactivable):
        _de_baja(TipoBaja.FALLECIMIENTO).reactivar(
            actor=ADMIN, es_administrador=True, ahora=AHORA, origen=MOSTRADOR
        )


@pytest.mark.ca("CA-SOC-14")
def test_la_inhabilitacion_administrativa_sobrevive_a_la_baja_y_la_reactivacion():
    s = socio()
    s.inhabilitar("Daño reiterado de material", actor=ADMIN, ahora=AHORA)
    s.dar_de_baja(
        SIN_NADA, A_PEDIDO, "Se mudó de ciudad", actor=ADMIN, es_administrador=True, ahora=AHORA
    )
    assert s.causas == {MotivoInhabilitacion.ADMINISTRATIVA}

    s.reactivar(actor=BIBLIO, es_administrador=False, ahora=AHORA, origen=MOSTRADOR)

    assert s.estado == EstadoSocio.INHABILITADO
    assert s.motivo_inhabilitacion == MotivoInhabilitacion.ADMINISTRATIVA
    assert s.motivo_administrativo == "Daño reiterado de material"


@pytest.mark.ca("CA-SOC-15")
def test_la_solicitud_de_reactivacion_queda_pendiente_y_al_reactivar_se_resuelve():
    s = _de_baja()

    s.solicitar_reactivacion("  Volví a la ciudad  ", actor=SOCIA, ahora=AHORA)

    assert s.solicitud is not None and s.solicitud.mensaje == "Volví a la ciudad"
    with pytest.raises(SolicitudYaPendiente):
        s.solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)
    s.reactivar(actor=BIBLIO, es_administrador=False, ahora=AHORA, origen="Solicitud aprobada")
    assert s.estado == EstadoSocio.HABILITADO and s.solicitud is None


def test_solo_pide_la_reactivacion_un_socio_en_baja_que_no_fallecio():
    with pytest.raises(SocioYaActivo):
        socio().solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)
    with pytest.raises(SocioNoReactivable):
        _de_baja(TipoBaja.FALLECIMIENTO).solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)
    with pytest.raises(ErrorDeValidacion):
        _de_baja().solicitar_reactivacion("x" * 301, actor=SOCIA, ahora=AHORA)


@pytest.mark.ca("CA-SOC-16")
def test_rechazar_la_solicitud_la_cierra_con_motivo_y_el_socio_puede_volver_a_pedir():
    s = _de_baja()
    with pytest.raises(SinSolicitudPendiente):
        s.rechazar_solicitud("Faltan datos", actor=BIBLIO, es_administrador=False, ahora=AHORA)
    s.solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)

    s.rechazar_solicitud(
        "Debe acercarse con su documento", actor=BIBLIO, es_administrador=False, ahora=AHORA
    )

    assert s.estado == EstadoSocio.BAJA and s.solicitud is None
    rechazo = s.eventos_pendientes[-1]
    assert (rechazo.tipo, rechazo.motivo) == (
        TipoEventoSocio.SOLICITUD_RECHAZADA,
        "Debe acercarse con su documento",
    )
    s.solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)


def test_la_solicitud_de_una_baja_administrativa_la_resuelve_solo_el_administrador():
    s = _de_baja(TipoBaja.ADMINISTRATIVA)
    s.solicitar_reactivacion(None, actor=SOCIA, ahora=AHORA)

    with pytest.raises(PermisoDenegado):
        s.rechazar_solicitud("No corresponde", actor=BIBLIO, es_administrador=False, ahora=AHORA)
    s.rechazar_solicitud("No corresponde", actor=ADMIN, es_administrador=True, ahora=AHORA)


# --- historial ----------------------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-18")
def test_cada_cambio_queda_en_el_historial_con_autor_y_origen():
    s = socio()
    s.modificar(replace(s.datos, apellido="Gómez Paz"), actor=ADMIN, ahora=AHORA)
    s.reevaluar(CON_VENCIDO, actor=None, ahora=AHORA, origen="Préstamo P-2026-0001 vencido")
    s.reevaluar(SIN_NADA, actor=BIBLIO, ahora=AHORA, origen="Devolución del préstamo P-2026-0001")

    tipos = [e.tipo for e in s.eventos_pendientes]
    assert tipos == [
        TipoEventoSocio.ALTA,
        TipoEventoSocio.MODIFICACION,
        TipoEventoSocio.CAMBIO_AUTOMATICO,
        TipoEventoSocio.CAMBIO_AUTOMATICO,
    ]
    _, modificacion, vencido, devuelto = s.eventos_pendientes
    assert [(c.campo, c.antes, c.despues) for c in modificacion.cambios] == [
        ("apellido", "Gómez", "Gómez Paz")
    ]
    assert vencido.usuario is None and vencido.origen == "Préstamo P-2026-0001 vencido"
    assert (vencido.estado_anterior, vencido.estado_nuevo) == (
        EstadoSocio.HABILITADO,
        EstadoSocio.INHABILITADO,
    )
    assert devuelto.estado_nuevo == EstadoSocio.HABILITADO and devuelto.usuario == BIBLIO


def test_la_baja_y_la_reactivacion_quedan_en_el_historial():
    s = _de_baja(TipoBaja.ADMINISTRATIVA)
    s.reactivar(actor=ADMIN, es_administrador=True, ahora=AHORA, origen=MOSTRADOR)

    baja, reactivacion = s.eventos_pendientes[-2:]
    assert (baja.tipo, baja.motivo, baja.estado_nuevo) == (
        TipoEventoSocio.BAJA,
        "Motivo de la baja",
        EstadoSocio.BAJA,
    )
    assert [(c.campo, c.despues) for c in baja.cambios] == [("tipo_baja", "ADMINISTRATIVA")]
    assert (reactivacion.tipo, reactivacion.origen) == (TipoEventoSocio.REACTIVACION, MOSTRADOR)
