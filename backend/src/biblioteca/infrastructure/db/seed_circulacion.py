"""Circulación de demostración: usuarios, préstamos, envíos, devoluciones, multas y reservas.

Arma una historia de unos 45 días coherente con las máquinas de estado y la matriz de
efectos (ARCHITECTURE.md §4.4 y §4.5), para que el tablero, los listados y los reportes
tengan datos. Las fechas se calculan hacia atrás desde `ahora`: así un préstamo "vencido"
o un remito "demorado" lo siguen siendo el día que se carga la demo.

Los usuarios de demostración tienen una contraseña inutilizable: el login (argon2 + JWT)
todavía no existe y el primer ADMIN real lo creará el seed desde variables de entorno.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from biblioteca.domain.enums import (
    CondicionFisica,
    EstadoEjemplar,
    EstadoMulta,
    EstadoPrestamo,
    EstadoRemito,
    EstadoReserva,
    MotivoBaja,
    MotivoCancelacion,
    ResultadoRevision,
    Rol,
    Sentido,
    TipoNotificacion,
)
from biblioteca.infrastructure.db.insercion import insertar
from biblioteca.infrastructure.db.secuencias import (
    formatear_numero_remito,
    secuencia_remito,
    siguiente_valor,
)
from biblioteca.infrastructure.db.tables import (
    devolucion,
    ejemplar,
    libro,
    movimiento_remito,
    multa,
    notificacion,
    parametro,
    prestamo,
    remito,
    reserva,
    sede,
    socio,
    usuario,
)

# Hash imposible de verificar: estos usuarios no pueden iniciar sesión.
CLAVE_INUTILIZABLE = "!demo-sin-acceso"

_USUARIOS_DEMO = (
    ("admin", "Administración de la red", Rol.ADMIN, None),
    ("bib.central", "Laura Medina", Rol.BIBLIOTECARIO, "CEN"),
    ("bib.norte", "Martín Ríos", Rol.BIBLIOTECARIO, "NOR"),
    ("bib.sur", "Sofía Herrera", Rol.BIBLIOTECARIO, "SUR"),
    ("log.central", "Pablo Ortiz", Rol.LOGISTICA, "CEN"),
)

# Un paso del remito: (estado al que pasa, cuándo, username del responsable, observación).
Paso = tuple[EstadoRemito, datetime, str, str | None]


class _Demo:
    """Ayudantes para insertar filas coherentes entre sí."""

    def __init__(self, conn: Connection, ahora: datetime) -> None:
        self.conn = conn
        self.ahora = ahora
        self.sedes = {c: i for c, i in conn.execute(select(sede.c.codigo, sede.c.id))}
        self.socios = {dni: i for dni, i in conn.execute(select(socio.c.dni, socio.c.id))}
        self.ejemplares = {
            c: i for c, i in conn.execute(select(ejemplar.c.codigo_inventario, ejemplar.c.id))
        }
        self.libros = {t: i for t, i in conn.execute(select(libro.c.titulo, libro.c.id))}
        parametros = {c: v for c, v in conn.execute(select(parametro.c.clave, parametro.c.valor))}
        self.plazo_dias = int(parametros["plazo_prestamo_dias"])
        self.multa_por_dia = int(parametros["multa_por_dia"])
        self.dias_para_retiro = int(parametros["dias_para_retiro"])
        self.usuarios: dict[str, int] = {}

    # ------------------------------------------------------------------ tiempo

    def hace(self, dias: int, horas: int = 0) -> datetime:
        return self.ahora - timedelta(days=dias, hours=horas)

    def dia(self, dias: int) -> date:
        return self.hace(dias).date()

    # ------------------------------------------------------------------ altas

    def crear_usuarios(self) -> None:
        for username, nombre, rol, codigo_sede in _USUARIOS_DEMO:
            self.usuarios[username] = insertar(
                self.conn,
                usuario,
                username=username,
                nombre_completo=nombre,
                password_hash=CLAVE_INUTILIZABLE,
                rol=rol,
                sede_id=self.sedes[codigo_sede] if codigo_sede else None,
            )

    def prestamo(
        self,
        dni: str,
        codigo_ejemplar: str,
        origen: str,
        destino: str,
        solicitado: datetime,
        registrado_por: str,
        estado: EstadoPrestamo,
        **otros: Any,
    ) -> int:
        return insertar(
            self.conn,
            prestamo,
            socio_id=self.socios[dni],
            ejemplar_id=self.ejemplares[codigo_ejemplar],
            sede_origen_id=self.sedes[origen],
            sede_destino_id=self.sedes[destino],
            estado=estado,
            fecha_solicitud=solicitado,
            registrado_por=self.usuarios[registrado_por],
            **otros,
        )

    def entrega(self, inicio: date) -> dict[str, date]:
        """Fechas de un préstamo entregado al socio (el vencimiento corre desde la entrega)."""
        return {"fecha_inicio": inicio, "fecha_vencimiento": inicio + timedelta(self.plazo_dias)}

    def remito(
        self,
        prestamo_id: int,
        codigo_ejemplar: str,
        sentido: Sentido,
        origen: str,
        destino: str,
        pasos: list[Paso],
        revision: ResultadoRevision | None = None,
    ) -> int:
        """Inserta el remito en su estado final y un movimiento por cada transición."""
        cuando = {estado: fecha for estado, fecha, _, _ in pasos}
        generado = pasos[0][1]
        anio = generado.year
        numero = formatear_numero_remito(anio, siguiente_valor(self.conn, secuencia_remito(anio)))
        observacion_revision = pasos[-1][3] if revision else None

        remito_id = insertar(
            self.conn,
            remito,
            numero=numero,
            ejemplar_id=self.ejemplares[codigo_ejemplar],
            prestamo_id=prestamo_id,
            sentido=sentido,
            sede_origen_id=self.sedes[origen],
            sede_destino_id=self.sedes[destino],
            estado=pasos[-1][0],
            fecha_generacion=generado,
            fecha_despacho=cuando.get(EstadoRemito.EN_TRANSITO),
            fecha_recepcion=cuando.get(EstadoRemito.RECIBIDO),
            resultado_revision=revision,
            observacion_revision=observacion_revision,
        )

        anterior: EstadoRemito | None = None
        for estado, fecha, username, observacion in pasos:
            self.conn.execute(
                insert(movimiento_remito).values(
                    remito_id=remito_id,
                    estado_anterior=anterior,
                    estado_nuevo=estado,
                    fecha_hora=fecha,
                    usuario_id=self.usuarios[username],
                    observacion=observacion,
                )
            )
            anterior = estado
        return remito_id

    def devolucion(
        self,
        prestamo_id: int,
        cuando: datetime,
        condicion: CondicionFisica,
        registrado_por: str,
        observacion: str | None = None,
    ) -> None:
        insertar(
            self.conn,
            devolucion,
            prestamo_id=prestamo_id,
            fecha_hora=cuando,
            condicion_fisica=condicion,
            observacion=observacion,
            registrado_por=self.usuarios[registrado_por],
        )

    def multa(
        self,
        prestamo_id: int,
        dias_atraso: int,
        generada: datetime,
        saldada: tuple[datetime, str] | None = None,
    ) -> None:
        insertar(
            self.conn,
            multa,
            prestamo_id=prestamo_id,
            dias_atraso=dias_atraso,
            monto_por_dia=self.multa_por_dia,
            monto=dias_atraso * self.multa_por_dia,
            estado=EstadoMulta.SALDADA if saldada else EstadoMulta.PENDIENTE,
            fecha_generacion=generada,
            fecha_saldada=saldada[0] if saldada else None,
            saldada_por=self.usuarios[saldada[1]] if saldada else None,
        )

    def reserva(
        self,
        dni: str,
        titulo: str,
        codigo_sede: str,
        solicitada: datetime,
        registrado_por: str,
        estado: EstadoReserva,
        **otros: Any,
    ) -> int:
        return insertar(
            self.conn,
            reserva,
            socio_id=self.socios[dni],
            libro_id=self.libros[titulo],
            sede_id=self.sedes[codigo_sede],
            estado=estado,
            fecha_solicitud=solicitada,
            registrado_por=self.usuarios[registrado_por],
            **otros,
        )

    def notificar(self, dni: str, tipo: TipoNotificacion, cuando: datetime, **refs: Any) -> None:
        mensajes = {
            TipoNotificacion.LISTO_PARA_RETIRO: "Tu préstamo está listo para retirar.",
            TipoNotificacion.RESERVA_ASIGNADA: "Tu reserva tiene un ejemplar asignado.",
            TipoNotificacion.MULTA_GENERADA: "Se generó una multa por atraso en la devolución.",
            TipoNotificacion.PRESTAMO_CANCELADO: (
                "Tu préstamo fue cancelado por un problema en el envío."
            ),
        }
        insertar(
            self.conn,
            notificacion,
            socio_id=self.socios[dni],
            tipo=tipo,
            mensaje=mensajes[tipo],
            fecha_hora=cuando,
            **refs,
        )

    def estado_ejemplar(
        self,
        codigo: str,
        estado: EstadoEjemplar,
        condicion: CondicionFisica | None = None,
        baja: tuple[MotivoBaja, date] | None = None,
    ) -> None:
        valores: dict[str, Any] = {"estado": estado}
        if condicion:
            valores["condicion_fisica"] = condicion
        if baja:
            valores["motivo_baja"], valores["fecha_baja"] = baja
        self.conn.execute(
            update(ejemplar).where(ejemplar.c.codigo_inventario == codigo).values(**valores)
        )


# DNI de los socios de la demo (seed.py): Ana, Bruno, Carla y Diego. Elena está inhabilitada.
ANA, BRUNO, CARLA, DIEGO = "30111222", "31222333", "32333444", "33444555"


def cargar_circulacion_demo(conn: Connection, ahora: datetime | None = None) -> None:
    """Carga la historia de demostración sobre las sedes, ejemplares y socios de la demo."""
    d = _Demo(conn, ahora or datetime.now(UTC).replace(microsecond=0))
    d.crear_usuarios()
    E, P, R = EstadoRemito, EstadoPrestamo, ResultadoRevision

    # --- Historia cerrada -------------------------------------------------------------

    # Préstamo local devuelto con 4 días de atraso: multa ya saldada.
    p = d.prestamo(
        ANA,
        "CEN-000001",
        "CEN",
        "CEN",
        d.hace(28),
        "bib.central",
        P.DEVUELTO,
        fecha_cierre=d.hace(10),
        **d.entrega(d.dia(28)),
    )
    d.devolucion(p, d.hace(10), CondicionFisica.BUENA, "bib.central")
    d.multa(p, 4, d.hace(10), saldada=(d.hace(9), "admin"))

    # Inter-sedes completo: ida y vuelta conformes. Al volver, se asigna a la reserva de Diego.
    p = d.prestamo(
        ANA,
        "NOR-000003",
        "NOR",
        "CEN",
        d.hace(30),
        "bib.central",
        P.DEVUELTO,
        fecha_limite_retiro=d.dia(27) + timedelta(d.dias_para_retiro),
        fecha_cierre=d.hace(13),
        **d.entrega(d.dia(26)),
    )
    d.remito(
        p,
        "NOR-000003",
        Sentido.IDA,
        "NOR",
        "CEN",
        [
            (E.GENERADO, d.hace(30), "bib.central", None),
            (E.EMPAQUETADO, d.hace(29, 20), "bib.norte", None),
            (E.EN_TRANSITO, d.hace(29), "bib.norte", None),
            (E.RECIBIDO, d.hace(27), "bib.central", "Llegó en buen estado"),
        ],
        R.CONFORME,
    )
    d.devolucion(p, d.hace(13), CondicionFisica.BUENA, "bib.central")
    d.remito(
        p,
        "NOR-000003",
        Sentido.VUELTA,
        "CEN",
        "NOR",
        [
            (E.GENERADO, d.hace(13), "bib.central", None),
            (E.EMPAQUETADO, d.hace(5), "log.central", None),
            (E.EN_TRANSITO, d.hace(4), "log.central", None),
            (E.RECIBIDO, d.hace(1), "bib.norte", "Sin novedades"),
        ],
        R.CONFORME,
    )
    r = d.reserva(
        DIEGO,
        "Ficciones",
        "NOR",
        d.hace(10),
        "bib.norte",
        EstadoReserva.ASIGNADA,
        ejemplar_asignado_id=d.ejemplares["NOR-000003"],
        fecha_asignacion=d.hace(1),
        fecha_limite=d.dia(1) + timedelta(d.dias_para_retiro),
    )
    d.notificar(DIEGO, TipoNotificacion.RESERVA_ASIGNADA, d.hace(1), reserva_id=r)
    d.estado_ejemplar("NOR-000003", EstadoEjemplar.RESERVADO)

    # Inter-sedes devuelto 6 días tarde y con uso: multa pendiente (Bruno no puede pedir más).
    p = d.prestamo(
        BRUNO,
        "SUR-000001",
        "SUR",
        "CEN",
        d.hace(35),
        "bib.central",
        P.DEVUELTO,
        fecha_limite_retiro=d.dia(33) + timedelta(d.dias_para_retiro),
        fecha_cierre=d.hace(12),
        **d.entrega(d.dia(32)),
    )
    d.remito(
        p,
        "SUR-000001",
        Sentido.IDA,
        "SUR",
        "CEN",
        [
            (E.GENERADO, d.hace(35), "bib.central", None),
            (E.EMPAQUETADO, d.hace(34, 20), "bib.sur", None),
            (E.EN_TRANSITO, d.hace(34), "bib.sur", None),
            (E.RECIBIDO, d.hace(33), "bib.central", "Llegó en buen estado"),
        ],
        R.CONFORME,
    )
    d.devolucion(p, d.hace(12), CondicionFisica.REGULAR, "bib.central", "Tapa con marcas de uso")
    d.multa(p, 6, d.hace(12))
    d.notificar(BRUNO, TipoNotificacion.MULTA_GENERADA, d.hace(12), prestamo_id=p)
    d.remito(
        p,
        "SUR-000001",
        Sentido.VUELTA,
        "CEN",
        "SUR",
        [
            (E.GENERADO, d.hace(12), "bib.central", None),
            (E.EMPAQUETADO, d.hace(11, 20), "log.central", None),
            (E.EN_TRANSITO, d.hace(11), "log.central", None),
            (E.RECIBIDO, d.hace(9), "bib.sur", "Desgaste de uso, sin daños"),
        ],
        R.CONFORME,
    )
    d.estado_ejemplar("SUR-000001", EstadoEjemplar.DISPONIBLE, CondicionFisica.REGULAR)

    # Inter-sedes devuelto a tiempo, pero la vuelta llega destruida: baja sin penalizar al socio.
    p = d.prestamo(
        BRUNO,
        "SUR-000002",
        "SUR",
        "NOR",
        d.hace(45),
        "bib.norte",
        P.DEVUELTO,
        fecha_limite_retiro=d.dia(42) + timedelta(d.dias_para_retiro),
        fecha_cierre=d.hace(28),
        **d.entrega(d.dia(41)),
    )
    d.remito(
        p,
        "SUR-000002",
        Sentido.IDA,
        "SUR",
        "NOR",
        [
            (E.GENERADO, d.hace(45), "bib.norte", None),
            (E.EMPAQUETADO, d.hace(44, 20), "bib.sur", None),
            (E.EN_TRANSITO, d.hace(44), "bib.sur", None),
            (E.RECIBIDO, d.hace(42), "bib.norte", "Llegó en buen estado"),
        ],
        R.CONFORME,
    )
    d.devolucion(p, d.hace(28), CondicionFisica.BUENA, "bib.norte")
    d.remito(
        p,
        "SUR-000002",
        Sentido.VUELTA,
        "NOR",
        "SUR",
        [
            (E.GENERADO, d.hace(28), "bib.norte", None),
            (E.EMPAQUETADO, d.hace(27, 20), "bib.norte", None),
            (E.EN_TRANSITO, d.hace(27), "bib.norte", None),
            (E.RECIBIDO, d.hace(24), "bib.sur", "Daños por agua: irrecuperable"),
        ],
        R.DESTRUIDO,
    )
    d.estado_ejemplar("SUR-000002", EstadoEjemplar.BAJA, baja=(MotivoBaja.DESTRUCCION, d.dia(24)))

    # La ida llega dañada: se cancela el préstamo, vuelve y queda en revisión en su sede.
    p = d.prestamo(
        CARLA,
        "CEN-000004",
        "CEN",
        "SUR",
        d.hace(30),
        "bib.sur",
        P.CANCELADO,
        motivo_cancelacion=MotivoCancelacion.ENVIO_DANADO,
        fecha_cierre=d.hace(27),
    )
    d.remito(
        p,
        "CEN-000004",
        Sentido.IDA,
        "CEN",
        "SUR",
        [
            (E.GENERADO, d.hace(30), "bib.sur", None),
            (E.EMPAQUETADO, d.hace(29, 20), "log.central", None),
            (E.EN_TRANSITO, d.hace(29), "log.central", None),
            (E.RECIBIDO, d.hace(27), "bib.sur", "Lomo despegado"),
        ],
        R.DANADO,
    )
    d.notificar(CARLA, TipoNotificacion.PRESTAMO_CANCELADO, d.hace(27), prestamo_id=p)
    d.remito(
        p,
        "CEN-000004",
        Sentido.VUELTA,
        "SUR",
        "CEN",
        [
            (E.GENERADO, d.hace(27), "bib.sur", None),
            (E.EMPAQUETADO, d.hace(26, 20), "bib.sur", None),
            (E.EN_TRANSITO, d.hace(26), "bib.sur", None),
            (E.RECIBIDO, d.hace(24), "bib.central", "Confirmado: lomo despegado"),
        ],
        R.DANADO,
    )
    d.estado_ejemplar("CEN-000004", EstadoEjemplar.EN_REVISION, CondicionFisica.DANADA)

    # La ida se extravía: préstamo cancelado y ejemplar dado de baja.
    p = d.prestamo(
        DIEGO,
        "NOR-000005",
        "NOR",
        "SUR",
        d.hace(21),
        "bib.sur",
        P.CANCELADO,
        motivo_cancelacion=MotivoCancelacion.ENVIO_EXTRAVIADO,
        fecha_cierre=d.hace(10),
    )
    d.remito(
        p,
        "NOR-000005",
        Sentido.IDA,
        "NOR",
        "SUR",
        [
            (E.GENERADO, d.hace(21), "bib.sur", None),
            (E.EMPAQUETADO, d.hace(20, 20), "bib.norte", None),
            (E.EN_TRANSITO, d.hace(20), "bib.norte", None),
            (E.EXTRAVIADO, d.hace(10), "bib.norte", "El transporte no lo encuentra"),
        ],
    )
    d.notificar(DIEGO, TipoNotificacion.PRESTAMO_CANCELADO, d.hace(10), prestamo_id=p)
    d.estado_ejemplar("NOR-000005", EstadoEjemplar.BAJA, baja=(MotivoBaja.EXTRAVIO, d.dia(10)))

    # Inter-sedes devuelto a tiempo: la vuelta todavía está viajando.
    p = d.prestamo(
        ANA,
        "NOR-000001",
        "NOR",
        "CEN",
        d.hace(18),
        "bib.central",
        P.DEVUELTO,
        fecha_limite_retiro=d.dia(16) + timedelta(d.dias_para_retiro),
        fecha_cierre=d.hace(3),
        **d.entrega(d.dia(15)),
    )
    d.remito(
        p,
        "NOR-000001",
        Sentido.IDA,
        "NOR",
        "CEN",
        [
            (E.GENERADO, d.hace(18), "bib.central", None),
            (E.EMPAQUETADO, d.hace(17, 20), "bib.norte", None),
            (E.EN_TRANSITO, d.hace(17), "bib.norte", None),
            (E.RECIBIDO, d.hace(16), "bib.central", "Llegó en buen estado"),
        ],
        R.CONFORME,
    )
    d.devolucion(p, d.hace(3), CondicionFisica.BUENA, "bib.central")
    d.remito(
        p,
        "NOR-000001",
        Sentido.VUELTA,
        "CEN",
        "NOR",
        [
            (E.GENERADO, d.hace(3), "bib.central", None),
            (E.EMPAQUETADO, d.hace(2, 20), "log.central", None),
            (E.EN_TRANSITO, d.hace(2), "log.central", None),
        ],
    )
    d.estado_ejemplar("NOR-000001", EstadoEjemplar.EN_TRANSITO)

    # --- Situación actual ---------------------------------------------------------------

    # Préstamos locales activos: uno vencido hace 6 días, uno que vence en 2 días y uno al día.
    d.prestamo(
        CARLA, "SUR-000003", "SUR", "SUR", d.hace(20), "bib.sur", P.ACTIVO, **d.entrega(d.dia(20))
    )
    d.prestamo(
        DIEGO,
        "CEN-000002",
        "CEN",
        "CEN",
        d.hace(12),
        "bib.central",
        P.ACTIVO,
        **d.entrega(d.dia(12)),
    )
    d.prestamo(
        DIEGO, "CEN-000005", "CEN", "CEN", d.hace(5), "bib.central", P.ACTIVO, **d.entrega(d.dia(5))
    )
    for codigo in ("SUR-000003", "CEN-000002", "CEN-000005"):
        d.estado_ejemplar(codigo, EstadoEjemplar.PRESTADO)

    # Ida en tránsito hace 9 días: supera dias_max_transito, el remito figura demorado.
    p = d.prestamo(ANA, "NOR-000002", "NOR", "CEN", d.hace(11), "bib.central", P.EN_ENVIO)
    d.remito(
        p,
        "NOR-000002",
        Sentido.IDA,
        "NOR",
        "CEN",
        [
            (E.GENERADO, d.hace(11), "bib.central", None),
            (E.EMPAQUETADO, d.hace(10), "bib.norte", None),
            (E.EN_TRANSITO, d.hace(9), "bib.norte", None),
        ],
    )
    d.estado_ejemplar("NOR-000002", EstadoEjemplar.EN_TRANSITO)

    # Ida recibida conforme: el préstamo espera que Ana lo retire en la sede Central.
    p = d.prestamo(
        ANA,
        "SUR-000004",
        "SUR",
        "CEN",
        d.hace(5),
        "bib.central",
        P.LISTO_PARA_RETIRO,
        fecha_limite_retiro=d.dia(2) + timedelta(d.dias_para_retiro),
    )
    d.remito(
        p,
        "SUR-000004",
        Sentido.IDA,
        "SUR",
        "CEN",
        [
            (E.GENERADO, d.hace(5), "bib.central", None),
            (E.EMPAQUETADO, d.hace(4, 20), "bib.sur", None),
            (E.EN_TRANSITO, d.hace(4), "bib.sur", None),
            (E.RECIBIDO, d.hace(2), "bib.central", "Llegó en buen estado"),
        ],
        R.CONFORME,
    )
    d.notificar(ANA, TipoNotificacion.LISTO_PARA_RETIRO, d.hace(2), prestamo_id=p)
    d.estado_ejemplar("SUR-000004", EstadoEjemplar.RESERVADO)

    # Idas que todavía no salieron: una empaquetada y otra recién generada.
    p = d.prestamo(CARLA, "CEN-000003", "CEN", "NOR", d.hace(1), "bib.norte", P.EN_ENVIO)
    d.remito(
        p,
        "CEN-000003",
        Sentido.IDA,
        "CEN",
        "NOR",
        [
            (E.GENERADO, d.hace(1), "bib.norte", None),
            (E.EMPAQUETADO, d.hace(0, 20), "log.central", None),
        ],
    )
    p = d.prestamo(DIEGO, "NOR-000004", "NOR", "SUR", d.hace(0, 3), "bib.sur", P.EN_ENVIO)
    d.remito(
        p,
        "NOR-000004",
        Sentido.IDA,
        "NOR",
        "SUR",
        [
            (E.GENERADO, d.hace(0, 3), "bib.sur", None),
        ],
    )
    for codigo in ("CEN-000003", "NOR-000004"):
        d.estado_ejemplar(codigo, EstadoEjemplar.PENDIENTE_DESPACHO)

    # Cola de reservas de Rayuela en la sede Sur (sus dos ejemplares están ocupados).
    d.reserva(DIEGO, "Rayuela", "SUR", d.hace(3), "bib.sur", EstadoReserva.PENDIENTE)
    d.reserva(CARLA, "Rayuela", "SUR", d.hace(1), "bib.sur", EstadoReserva.PENDIENTE)
    # Reserva cancelada por la socia.
    d.reserva(
        CARLA,
        "Don Quijote de la Mancha",
        "CEN",
        d.hace(4),
        "bib.central",
        EstadoReserva.CANCELADA,
        fecha_cierre=d.hace(2),
    )
