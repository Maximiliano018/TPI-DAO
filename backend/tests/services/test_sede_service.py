"""Casos de uso de sedes con repositorios y verificadores en memoria."""

from datetime import date, time

import pytest

from app.exceptions import (
    CodigoInmutable,
    ConflictoDeVersion,
    DireccionDuplicada,
    ErrorDeValidacion,
    ExcepcionHorarioInvalida,
    ExcepcionHorarioSuperpuesta,
    LocalidadInvalida,
    PermisoDenegado,
    SedeCodigoDuplicado,
    SedeConActividadPendiente,
    SedeEnBaja,
    SedeNoEncontrada,
    SedeNombreDuplicado,
    SedeYaActiva,
    SedeYaEnBaja,
)
from app.models.horario import TipoExcepcion
from app.models.policies.verificacion_baja_sede import TipoImpedimento
from app.models.sede import EstadoSede, TipoEventoSede
from app.models.valores import FranjaHoraria
from app.repositories.interfaces.sede_repository import FiltroEstado, OrdenSedes
from app.services.sede_service import DatosExcepcion, SedeService
from tests.factories.dominio import BibliotecarioFactory, SocioUsuarioFactory, UsuarioFactory
from tests.factories.sede import datos_sede
from tests.fakes.repositorios import UnitOfWorkEnMemoria
from tests.fakes.verificadores import verificador_con

ADMIN = UsuarioFactory(id=1, nombre="Admin")
BIBLIO = BibliotecarioFactory(id=2)
SOCIO = SocioUsuarioFactory(id=3)


@pytest.fixture
def uow() -> UnitOfWorkEnMemoria:
    return UnitOfWorkEnMemoria()


@pytest.fixture
def servicio(uow, reloj) -> SedeService:
    return SedeService(uow, reloj, verificador_con())


def _crear(servicio, codigo="CEN", **over):
    return servicio.crear(ADMIN, codigo, datos_sede(**over)).sede


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-01", "CA-SED-34", "CA-ACC-06")
def test_el_alta_crea_la_sede_activa_y_la_confirma(servicio, uow):
    vista = servicio.crear(ADMIN, "cen", datos_sede(nombre="Sede Central"))

    sede = vista.sede
    assert sede.id is not None and sede.estado == EstadoSede.ACTIVA and sede.codigo.valor == "CEN"
    assert sede.creado_por.id == 1 and sede.actualizado_por.id == 1
    assert uow.confirmaciones == 1
    [evento] = uow.sedes.eventos[sede.id]
    assert evento.tipo == TipoEventoSede.ALTA and evento.usuario.id == 1


@pytest.mark.ca("CA-SED-46")
@pytest.mark.parametrize("usuario", [BIBLIO, SOCIO])
def test_solo_el_administrador_administra_sedes(servicio, uow, usuario):
    sede = _crear(servicio)

    with pytest.raises(PermisoDenegado):
        servicio.crear(usuario, "OTRA", datos_sede())
    with pytest.raises(PermisoDenegado):
        servicio.modificar(usuario, sede.id, 1, datos_sede())
    with pytest.raises(PermisoDenegado):
        servicio.dar_de_baja(usuario, sede.id, 1, "Cierre definitivo")
    with pytest.raises(PermisoDenegado):
        servicio.reactivar(usuario, sede.id, 1)
    with pytest.raises(PermisoDenegado):
        servicio.agregar_excepciones(
            usuario, sede.id, DatosExcepcion(date(2027, 1, 1), None, TipoExcepcion.CIERRE_TOTAL)
        )


@pytest.mark.ca("CA-SED-02")
def test_el_nombre_es_unico_sin_distinguir_mayusculas_ni_tildes(servicio):
    _crear(servicio, "CEN", nombre="Centro")

    with pytest.raises(SedeNombreDuplicado) as error:
        servicio.crear(ADMIN, "OTRA", datos_sede(nombre="CÉNTRO"))

    assert error.value.detalles[0]["sede"]["codigo"] == "CEN"


@pytest.mark.ca("CA-SED-13")
def test_el_codigo_es_unico_sin_distinguir_mayusculas(servicio):
    _crear(servicio, "CEN")

    with pytest.raises(SedeCodigoDuplicado):
        servicio.crear(ADMIN, "cen", datos_sede())


@pytest.mark.ca("CA-SED-38")
def test_una_localidad_fuera_del_catalogo_se_rechaza(servicio):
    with pytest.raises(LocalidadInvalida) as error:
        servicio.crear(ADMIN, "CEN", datos_sede(localidad_id=999))

    assert error.value.detalles[0]["campo"] == "localidad_id"


@pytest.mark.ca("CA-SED-03")
def test_una_direccion_repetida_advierte_y_se_puede_corregir_o_confirmar(servicio, uow):
    existente = _crear(servicio, "CEN", calle="Av. Colón", numero="250")

    with pytest.raises(DireccionDuplicada) as error:
        servicio.crear(ADMIN, "NORTE", datos_sede(calle="AVENIDA Colon", numero="0250"))
    assert error.value.detalles[0]["sede"]["id"] == existente.id
    assert "Sede" in error.value.mensaje and uow.sedes.buscar_por_codigo("NORTE") is None

    # corregir la dirección y reintentar
    servicio.crear(ADMIN, "NORTE", datos_sede(calle="Av. Colón", numero="251"))
    # confirmar la duplicación
    confirmada = servicio.crear(
        ADMIN,
        "SUR",
        datos_sede(calle="Av. Colón", numero="250"),
        confirmar_direccion_duplicada=True,
    )
    campos = [c.campo for c in uow.sedes.eventos[confirmada.sede.id][0].cambios]
    assert "direccion_duplicada_confirmada" in campos


def test_una_direccion_en_otra_localidad_no_es_duplicada(servicio):
    _crear(servicio, "CEN", calle="Colón", numero="250", localidad_id=1)

    servicio.crear(ADMIN, "RCUARTO", datos_sede(calle="Colón", numero="250", localidad_id=2))


def test_con_formato_invalido_no_se_persiste_nada(servicio, uow):
    with pytest.raises(ErrorDeValidacion):
        servicio.crear(ADMIN, "CEN", datos_sede(telefono="123"))

    assert uow.sedes.sedes == {} and uow.reversiones == 1


def test_el_formato_se_valida_antes_que_los_duplicados(servicio):
    _crear(servicio, "CEN")

    # Código duplicado y nombre inválido: gana la validación de forma (422), no el 409.
    with pytest.raises(ErrorDeValidacion) as error:
        servicio.crear(ADMIN, "CEN", datos_sede(nombre="AB"))

    assert error.value.detalles[0]["campo"] == "nombre"


# --- modificación ----------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-35")
def test_modificar_guarda_el_cambio_incrementa_la_version_y_audita(servicio, uow):
    sede = _crear(servicio, "CEN", nombre="Central")

    vista = servicio.modificar(
        UsuarioFactory(id=5, nombre="Otro Admin"),
        sede.id,
        1,
        datos_sede(nombre="Central 2", telefono="+543514000000"),
    )

    assert vista.sede.version == 2 and vista.sede.nombre == "Central 2"
    assert vista.sede.actualizado_por.id == 5 and vista.sede.creado_por.id == 1
    evento = uow.sedes.eventos[sede.id][-1]
    assert evento.tipo == TipoEventoSede.MODIFICACION
    assert {c.campo for c in evento.cambios} == {"nombre", "numero", "telefono"}


@pytest.mark.ca("CA-SED-14")
def test_el_codigo_es_inmutable(servicio):
    sede = _crear(servicio, "CEN")

    with pytest.raises(CodigoInmutable):
        servicio.modificar(ADMIN, sede.id, 1, datos_sede(), codigo="OTRO")

    # enviar el mismo código (en cualquier capitalización) es aceptado
    servicio.modificar(ADMIN, sede.id, 1, datos_sede(), codigo="cen")
    assert servicio.obtener(ADMIN, sede.id).sede.codigo.valor == "CEN"


@pytest.mark.ca("CA-SED-12")
def test_modificar_a_un_nombre_existente_se_rechaza_pero_no_contra_si_misma(servicio):
    _crear(servicio, "CEN", nombre="Centro")
    otra = _crear(servicio, "NORTE", nombre="Norte")

    with pytest.raises(SedeNombreDuplicado):
        servicio.modificar(ADMIN, otra.id, 1, datos_sede(nombre="centro"))
    servicio.modificar(ADMIN, otra.id, 1, datos_sede(nombre="NORTE", calle="Otra calle"))


@pytest.mark.ca("CA-SED-15")
def test_una_sede_en_baja_no_se_edita_hasta_reactivarla(servicio):
    sede = _crear(servicio, "CEN")
    servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre temporal")

    with pytest.raises(SedeEnBaja):
        servicio.modificar(ADMIN, sede.id, 2, datos_sede())
    with pytest.raises(SedeEnBaja):
        servicio.agregar_excepciones(
            ADMIN, sede.id, DatosExcepcion(date(2027, 1, 1), None, TipoExcepcion.CIERRE_TOTAL)
        )

    servicio.reactivar(ADMIN, sede.id, 2)
    servicio.modificar(ADMIN, sede.id, 3, datos_sede(nombre="Reabierta"))


@pytest.mark.ca("CA-SED-41")
def test_una_version_desactualizada_se_rechaza_e_informa_la_actual(servicio):
    sede = _crear(servicio, "CEN")
    servicio.modificar(ADMIN, sede.id, 1, datos_sede(nombre="Cambio de A"))

    with pytest.raises(ConflictoDeVersion) as error:
        servicio.modificar(ADMIN, sede.id, 1, datos_sede(nombre="Cambio de B"))

    assert error.value.detalles[0]["version_actual"] == 2
    with pytest.raises(ConflictoDeVersion):
        servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre definitivo")


def test_la_direccion_solo_se_revalida_si_cambio_el_domicilio(servicio):
    _crear(servicio, "CEN", calle="Colón", numero="250")
    duplicada = servicio.crear(
        ADMIN, "DUP", datos_sede(nombre="Duplicada", calle="Colón", numero="250"), True
    ).sede

    # no cambió el domicilio: editar otro dato no vuelve a advertir
    servicio.modificar(
        ADMIN, duplicada.id, 1, datos_sede(nombre="Duplicada 2", calle="Colón", numero="250")
    )
    # cambió a otro domicilio ocupado: advierte
    _crear(servicio, "OTRA", calle="Sobremonte", numero="10")
    with pytest.raises(DireccionDuplicada):
        servicio.modificar(
            ADMIN,
            duplicada.id,
            2,
            datos_sede(nombre="Duplicada 2", calle="Sobremonte", numero="10"),
        )


def test_un_alta_sin_cambios_efectivos_no_genera_evento_ni_version(servicio, uow):
    sede = _crear(servicio, "CEN", nombre="Central", calle="Colón", numero="1")
    cantidad = len(uow.sedes.eventos[sede.id])

    servicio.modificar(ADMIN, sede.id, 1, datos_sede(nombre="Central", calle="Colón", numero="1"))

    assert servicio.obtener(ADMIN, sede.id).sede.version == 1
    assert len(uow.sedes.eventos[sede.id]) == cantidad


# --- baja y reactivación ---------------------------------------------------------------------

TIPOS_QUE_BLOQUEAN = [
    ("PRESTAMOS_EN_CURSO", "CA-SED-05"),
    ("REMITOS_ABIERTOS", "CA-SED-06"),
    ("RESERVAS_PENDIENTES", "CA-SED-19"),
    ("EJEMPLARES_EN_SEDE", "CA-SED-17"),
    ("EJEMPLARES_PROPIOS_FUERA", "CA-SED-18"),
    ("BIBLIOTECARIOS_ASIGNADOS", "CA-SED-16"),
]


@pytest.mark.parametrize(("tipo", "criterio"), TIPOS_QUE_BLOQUEAN)
def test_cada_tipo_de_actividad_pendiente_bloquea_la_baja(uow, reloj, tipo, criterio):
    servicio = SedeService(uow, reloj, verificador_con(**{tipo: 3}))
    sede = _crear(servicio, "CEN")
    estado_antes = (sede.estado, sede.version)

    with pytest.raises(SedeConActividadPendiente) as error:
        servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre definitivo")

    assert error.value.detalles[0]["tipo"] == tipo and error.value.detalles[0]["cantidad"] == 3
    assert (sede.estado, sede.version) == estado_antes
    assert uow.reversiones >= 1


@pytest.mark.ca(
    "CA-SED-20", "CA-SED-05", "CA-SED-06", "CA-SED-19", "CA-SED-17", "CA-SED-18", "CA-SED-16"
)
def test_todos_los_tipos_de_impedimento_estan_cubiertos_por_la_prueba_parametrizada():
    assert {t for t, _ in TIPOS_QUE_BLOQUEAN} == {t.value for t in TipoImpedimento}


@pytest.mark.ca("CA-SED-07", "CA-SED-23")
def test_la_baja_bloqueada_informa_todos_los_impedimentos_y_no_cambia_nada(uow, reloj):
    servicio = SedeService(
        uow,
        reloj,
        verificador_con(PRESTAMOS_EN_CURSO=2, REMITOS_ABIERTOS=1, BIBLIOTECARIOS_ASIGNADOS=1),
    )
    sede = _crear(servicio, "CEN", nombre="Centro")
    eventos = len(uow.sedes.eventos[sede.id])

    with pytest.raises(SedeConActividadPendiente) as error:
        servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre definitivo")

    assert "No se puede dar de baja la sede Centro" in error.value.mensaje
    assert "2 préstamos en curso, 1 remito abierto, 1 bibliotecario asignado" in error.value.mensaje
    assert len(error.value.detalles) == 3
    assert len(uow.sedes.eventos[sede.id]) == eventos
    assert sede.estado == EstadoSede.ACTIVA and sede.baja is None


@pytest.mark.ca("CA-SED-08", "CA-SED-21", "CA-SED-22")
def test_sin_actividad_pendiente_la_baja_procede_y_la_reactivacion_la_revierte(servicio, uow):
    sede = _crear(servicio, "CEN")

    baja = servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre por obras").sede
    assert baja.estado == EstadoSede.BAJA and baja.baja.motivo == "Cierre por obras"
    assert baja.baja.usuario.id == 1 and baja.version == 2

    activa = servicio.reactivar(ADMIN, sede.id, 2).sede
    assert activa.estado == EstadoSede.ACTIVA and activa.baja is None and activa.version == 3
    tipos = [e.tipo for e in uow.sedes.eventos[sede.id]]
    assert tipos == [TipoEventoSede.ALTA, TipoEventoSede.BAJA, TipoEventoSede.REACTIVACION]


def test_una_baja_bloqueada_se_acepta_cuando_la_actividad_se_resuelve(uow, reloj):
    pendiente = verificador_con(BIBLIOTECARIOS_ASIGNADOS=1)
    servicio = SedeService(uow, reloj, pendiente)
    sede = _crear(servicio, "CEN")
    with pytest.raises(SedeConActividadPendiente):
        servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre definitivo")

    resuelto = SedeService(uow, reloj, verificador_con())
    resuelto.dar_de_baja(ADMIN, sede.id, 1, "Cierre definitivo")

    assert sede.estado == EstadoSede.BAJA


@pytest.mark.ca("CA-SED-47")
def test_repetir_baja_o_reactivacion_informa_que_no_hay_nada_que_hacer(servicio):
    sede = _crear(servicio, "CEN")
    with pytest.raises(SedeYaActiva):
        servicio.reactivar(ADMIN, sede.id, 1)
    servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre temporal")

    with pytest.raises(SedeYaEnBaja):
        servicio.dar_de_baja(ADMIN, sede.id, 1, "Cierre temporal")


def test_una_sede_inexistente_responde_no_encontrada(servicio):
    for accion in (
        lambda: servicio.modificar(ADMIN, 99, 1, datos_sede()),
        lambda: servicio.dar_de_baja(ADMIN, 99, 1, "Cierre temporal"),
        lambda: servicio.reactivar(ADMIN, 99, 1),
        lambda: servicio.obtener(ADMIN, 99),
    ):
        with pytest.raises(SedeNoEncontrada):
            accion()


# --- consulta y visibilidad ------------------------------------------------------------------


def _con_cuatro_sedes(servicio):
    ids = [_crear(servicio, f"SED{n}", nombre=f"Sede {n}").id for n in range(1, 5)]
    servicio.dar_de_baja(ADMIN, ids[3], 1, "Cierre temporal")
    return ids


def _listar(servicio, usuario, estado=None, texto=None, orden=OrdenSedes.NOMBRE, page=1, size=20):
    return servicio.listar(usuario, estado, texto, None, orden, page, size)


@pytest.mark.ca("CA-SED-11")
def test_el_socio_lista_solo_sedes_activas_aunque_pida_las_de_baja(servicio):
    _con_cuatro_sedes(servicio)

    for estado in (None, FiltroEstado.BAJA, FiltroEstado.TODAS):
        pagina = _listar(servicio, SOCIO, estado)
        assert pagina.total == 3
        assert all(v.sede.estado == EstadoSede.ACTIVA for v in pagina.items)


@pytest.mark.ca("CA-SED-44")
def test_el_bibliotecario_ve_activas_por_defecto_y_puede_pedir_las_de_baja(servicio):
    _con_cuatro_sedes(servicio)

    assert _listar(servicio, BIBLIO).total == 3
    assert _listar(servicio, BIBLIO, FiltroEstado.BAJA).total == 1
    assert _listar(servicio, BIBLIO, FiltroEstado.TODAS).total == 4


def test_el_administrador_ve_todas_por_defecto(servicio):
    _con_cuatro_sedes(servicio)

    assert _listar(servicio, ADMIN).total == 4
    assert _listar(servicio, ADMIN, FiltroEstado.ACTIVA).total == 3


@pytest.mark.ca("CA-SED-43")
def test_el_listado_pagina_filtra_por_texto_y_ordena(servicio):
    _con_cuatro_sedes(servicio)

    primera = _listar(servicio, ADMIN, page=1, size=3)
    segunda = _listar(servicio, ADMIN, page=2, size=3)
    assert (primera.total, len(primera.items), len(segunda.items)) == (4, 3, 1)
    assert [v.sede.nombre for v in primera.items] == ["Sede 1", "Sede 2", "Sede 3"]

    assert [v.sede.codigo.valor for v in _listar(servicio, ADMIN, texto="Sede 2").items] == ["SED2"]
    descendente = _listar(servicio, ADMIN, orden=OrdenSedes.NOMBRE_DESC)
    assert descendente.items[0].sede.nombre == "Sede 4"


@pytest.mark.ca("CA-SED-45")
def test_un_socio_no_ve_el_detalle_de_una_sede_en_baja(servicio):
    ids = _con_cuatro_sedes(servicio)

    with pytest.raises(SedeNoEncontrada) as error:
        servicio.obtener(SOCIO, ids[3])

    assert error.value.mensaje == "La sede solicitada no existe o no está disponible."
    assert servicio.obtener(BIBLIO, ids[3]).sede.estado == EstadoSede.BAJA
    assert servicio.obtener(SOCIO, ids[0]).sede.id == ids[0]


def test_el_resumen_cuenta_sedes_por_estado_y_es_solo_del_administrador(servicio):
    _con_cuatro_sedes(servicio)

    assert servicio.resumen(ADMIN) == {"total": 4, "activas": 3, "en_baja": 1}
    with pytest.raises(PermisoDenegado):
        servicio.resumen(BIBLIO)


def test_la_vista_indica_si_la_sede_esta_abierta_ahora(servicio):
    sede = _crear(servicio, "CEN")  # el reloj fijo es martes 12:00; horario 9-13

    assert servicio.obtener(SOCIO, sede.id).abierta_ahora is True


# --- excepciones de horario ------------------------------------------------------------------


@pytest.mark.ca("CA-SED-29", "CA-SED-33", "CA-SED-34")
def test_las_excepciones_se_agregan_por_rango_y_se_pueden_quitar(servicio, uow, reloj):
    sede = _crear(servicio, "CEN")

    creadas = servicio.agregar_excepciones(
        ADMIN,
        sede.id,
        DatosExcepcion(
            date(2026, 11, 10), date(2026, 11, 12), TipoExcepcion.CIERRE_TOTAL, motivo="Obras"
        ),
    )

    assert [e.fecha.day for e in creadas] == [10, 11, 12] and all(e.id for e in creadas)
    assert servicio.obtener(SOCIO, sede.id).abierta_ahora is False  # cierre total hoy
    servicio.quitar_excepcion(ADMIN, sede.id, creadas[0].id)
    assert servicio.obtener(SOCIO, sede.id).abierta_ahora is True
    assert servicio.obtener(SOCIO, sede.id).sede.version == 1  # no incrementan la versión
    tipos = [e.tipo for e in uow.sedes.eventos[sede.id]]
    assert tipos[-2:] == [TipoEventoSede.EXCEPCION_AGREGADA, TipoEventoSede.EXCEPCION_ELIMINADA]


def test_el_alta_de_excepciones_devuelve_solo_las_creadas(servicio):
    sede = _crear(servicio, "CEN")
    dia = date(2026, 12, 1)
    servicio.agregar_excepciones(
        ADMIN, sede.id, DatosExcepcion(dia, None, TipoExcepcion.CIERRE_PARCIAL, time(9), time(10))
    )

    creadas = servicio.agregar_excepciones(
        ADMIN, sede.id, DatosExcepcion(dia, None, TipoExcepcion.CIERRE_PARCIAL, time(14), time(15))
    )

    assert [(e.desde, e.hasta) for e in creadas] == [(time(14), time(15))]


def test_un_rango_de_mas_de_31_dias_o_invertido_se_rechaza(servicio):
    sede = _crear(servicio, "CEN")

    with pytest.raises(ExcepcionHorarioInvalida):
        servicio.agregar_excepciones(
            ADMIN,
            sede.id,
            DatosExcepcion(date(2026, 12, 1), date(2027, 1, 1), TipoExcepcion.CIERRE_TOTAL),
        )
    with pytest.raises(ExcepcionHorarioInvalida):
        servicio.agregar_excepciones(
            ADMIN,
            sede.id,
            DatosExcepcion(date(2026, 12, 5), date(2026, 12, 1), TipoExcepcion.CIERRE_TOTAL),
        )
    servicio.agregar_excepciones(
        ADMIN,
        sede.id,
        DatosExcepcion(date(2026, 12, 1), date(2026, 12, 31), TipoExcepcion.CIERRE_TOTAL),
    )


@pytest.mark.ca("CA-SED-31", "CA-SED-30")
def test_la_superposicion_rechaza_el_rango_completo(servicio):
    sede = _crear(servicio, "CEN")
    servicio.agregar_excepciones(
        ADMIN,
        sede.id,
        DatosExcepcion(date(2026, 12, 2), None, TipoExcepcion.CIERRE_PARCIAL, time(9), time(12)),
    )

    with pytest.raises(ExcepcionHorarioSuperpuesta):
        servicio.agregar_excepciones(
            ADMIN,
            sede.id,
            DatosExcepcion(date(2026, 12, 1), date(2026, 12, 3), TipoExcepcion.CIERRE_TOTAL),
        )

    assert len(servicio.excepciones(ADMIN, sede.id)) == 1


def test_las_excepciones_pasadas_las_ve_solo_el_administrador(servicio, uow):
    sede = _crear(servicio, "CEN")
    from dataclasses import replace

    from app.models.horario import ExcepcionHorario

    uow.sedes.sedes[sede.id].excepciones = [
        ExcepcionHorario(id=1, fecha=date(2026, 11, 1), tipo=TipoExcepcion.CIERRE_TOTAL),
        ExcepcionHorario(id=2, fecha=date(2026, 12, 1), tipo=TipoExcepcion.CIERRE_TOTAL),
    ]
    assert replace  # (silencia importación opcional)

    assert [e.id for e in servicio.excepciones(ADMIN, sede.id, incluir_pasadas=True)] == [1, 2]
    assert [e.id for e in servicio.excepciones(ADMIN, sede.id)] == [2]
    assert [e.id for e in servicio.excepciones(BIBLIO, sede.id, incluir_pasadas=True)] == [2]
    assert [e.id for e in servicio.excepciones(SOCIO, sede.id)] == [2]


# --- historial -------------------------------------------------------------------------------


@pytest.mark.ca("CA-SED-37")
def test_el_historial_es_solo_del_administrador(servicio):
    sede = _crear(servicio, "CEN")

    for usuario in (BIBLIO, SOCIO):
        with pytest.raises(PermisoDenegado):
            servicio.historial(usuario, sede.id, 1, 20)


@pytest.mark.ca("CA-SED-34", "CA-SED-35", "CA-SED-36")
def test_el_historial_lista_los_eventos_del_mas_reciente_al_mas_antiguo(servicio):
    sede = _crear(servicio, "CEN")
    servicio.modificar(ADMIN, sede.id, 1, datos_sede(nombre="Nuevo"))
    servicio.dar_de_baja(ADMIN, sede.id, 2, "Cierre temporal")
    servicio.reactivar(ADMIN, sede.id, 3)

    pagina = servicio.historial(ADMIN, sede.id, 1, 20)

    assert [e.tipo for e in pagina.items] == [
        TipoEventoSede.REACTIVACION,
        TipoEventoSede.BAJA,
        TipoEventoSede.MODIFICACION,
        TipoEventoSede.ALTA,
    ]
    assert pagina.total == 4
    solo_baja = servicio.historial(ADMIN, sede.id, 1, 20, tipo_evento=TipoEventoSede.BAJA)
    assert [e.motivo for e in solo_baja.items] == ["Cierre temporal"]
    with pytest.raises(SedeNoEncontrada):
        servicio.historial(ADMIN, 99, 1, 20)


def test_el_historial_filtra_por_dias_completos_en_la_zona_de_negocio(servicio, reloj):
    sede = _crear(servicio, "CEN")  # martes 10/11 12:00
    reloj.avanzar(horas=11)  # 10/11 23:00 en Córdoba (ya es 11/11 en UTC)
    servicio.modificar(ADMIN, sede.id, 1, datos_sede(nombre="Nuevo"))
    reloj.avanzar(horas=2)  # 11/11 01:00
    servicio.dar_de_baja(ADMIN, sede.id, 2, "Cierre temporal")

    def tipos(**filtros):
        return [e.tipo for e in servicio.historial(ADMIN, sede.id, 1, 20, **filtros).items]

    assert tipos(hasta=date(2026, 11, 10)) == [TipoEventoSede.MODIFICACION, TipoEventoSede.ALTA]
    assert tipos(desde=date(2026, 11, 11)) == [TipoEventoSede.BAJA]
    assert tipos(desde=date(2026, 11, 10), hasta=date(2026, 11, 11)) == [
        TipoEventoSede.BAJA,
        TipoEventoSede.MODIFICACION,
        TipoEventoSede.ALTA,
    ]
    with pytest.raises(ErrorDeValidacion):
        servicio.historial(
            ADMIN, sede.id, 1, 20, desde=date(2026, 11, 11), hasta=date(2026, 11, 10)
        )


def test_los_horarios_se_envian_como_objetos_de_dominio_validados(servicio):
    from app.exceptions import HorarioInvalido

    with pytest.raises(HorarioInvalido):
        servicio.crear(ADMIN, "CEN", datos_sede(horarios=[]))
    with pytest.raises(HorarioInvalido):
        servicio.crear(
            ADMIN,
            "CEN",
            datos_sede(
                horarios=[FranjaHoraria(1, time(9), time(13)), FranjaHoraria(1, time(12), time(14))]
            ),
        )


def test_el_catalogo_de_localidades_se_filtra_sin_distinguir_tildes(servicio):
    assert [loc.nombre for loc in servicio.localidades(None, "rio")] == ["Río Cuarto"]
    assert servicio.provincias() == [(1, "Córdoba")]
