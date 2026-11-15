"""Historia de demostración: 90 días de la red contados con los casos de uso reales.

Todo pasa por los servicios de la aplicación con un reloj que avanza desde hace 90 días hasta
hoy (``app/db/seed_demo.py``). Así cada dato tiene su historial, su auditoría (quién y cuándo) y
sus reglas aplicadas, y la demo recorre todos los estados de cada entidad:

* **Sedes:** altas, modificación, cierres por fecha (agregados y quitados), una baja con
  reactivación y una baja definitiva.
* **Personal:** dos administradores, un bibliotecario por sede activa y una suplente que se
  reasigna de sede y se da de baja.
* **Parámetros:** cambios auditados (multa por daño, por extravío, tope, renovaciones).
* **Socios:** cuentas, modificaciones, inhabilitación administrativa y rehabilitación,
  inhabilitación automática (vencidos y multas), bajas de los tres tipos, una solicitud de
  reactivación pendiente, una rechazada y una reactivación.
* **Catálogo:** libros, una revista y una obra de referencia (con y sin ISBN, varios autores),
  ejemplares en cinco sedes, una corrección del libro, cambio de estado físico, baja manual,
  reparación y recuperación de extraviados.
* **Préstamos:** locales y entre sedes, en mostrador (también por el administrador) y por
  autogestión del socio, en todos los estados: solicitado, en envío, activo, renovado, vencido,
  devuelto y cancelado (por el socio, por retiro vencido y por un envío dañado).
* **Remitos:** envío, retorno y traslado en los diez estados (generado, empaquetado,
  despachado, en tránsito, recibido, dañado, destruido, incompleto, extraviado y anulado), con
  sus incidencias a cargo de la sede origen.
* **Reservas:** pendiente, disponible para retiro, cumplida (local y entre sedes), cancelada (por
  el socio y por el administrador) y vencida.
* **Devoluciones y multas:** en término, tardías, retroactiva con motivo, dañada y extraviada;
  multas por atraso, daño y extravío, pagadas en el mostrador (débito, efectivo, transferencia)
  y en línea (con un rechazo de prueba y un pago en curso cancelado por un cobro en mostrador).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.security import hashear_clave
from app.db.models import (
    DetalleRemitoORM,
    LocalidadORM,
    PrestamoORM,
    RemitoORM,
    ReservaORM,
    UsuarioORM,
)
from app.db.portadas_demo import portada_de
from app.db.seed_demo import Demo
from app.models.devolucion import EstadoRecibido
from app.models.ejemplar import EstadoFisico
from app.models.horario import TipoExcepcion
from app.models.libro import TipoMaterial
from app.models.pago import FormaEnLinea, MedioPago
from app.models.remito import MotivoRemito
from app.models.socio import TipoBaja, TipoDocumento
from app.models.usuario import Rol, Usuario
from app.models.valores import FranjaHoraria
from app.services.catalogo_service import DatosEjemplarNuevo, DatosLibroNuevo
from app.services.sede_service import DatosExcepcion, DatosSede
from app.services.socio_service import DatosSocio
from app.services.usuario_service import DatosUsuarioNuevo

# --- datos de referencia ------------------------------------------------------------------------


@dataclass(frozen=True)
class SedeDemo:
    codigo: str
    nombre: str
    calle: str
    numero: str
    localidad: str
    telefono: str
    email: str
    responsable: str
    sabado: bool = True


SEDES = [
    SedeDemo(
        "CEN",
        "Sede Central",
        "Av. Colón",
        "1250",
        "Córdoba",
        "+543514221234",
        "central@red.example",
        "Laura Pérez",
    ),
    SedeDemo(
        "NORTE",
        "Sede Norte",
        "Av. Rafael Núñez",
        "4500",
        "Córdoba",
        "+543514000000",
        "norte@red.example",
        "Ana Gómez",
    ),
    SedeDemo(
        "SUR_RC",
        "Sede Río Cuarto",
        "Sobremonte",
        "120",
        "Río Cuarto",
        "+543584670000",
        "riocuarto@red.example",
        "Martín Díaz",
        sabado=False,
    ),
    SedeDemo(
        "VMARIA",
        "Sede Villa María",
        "Bv. España",
        "350",
        "Villa María",
        "+543534520000",
        "villamaria@red.example",
        "Graciela Ponce",
    ),
    SedeDemo(
        "OESTE_VCP",
        "Sede Villa Carlos Paz",
        "Av. San Martín",
        "800",
        "Villa Carlos Paz",
        "+543541420000",
        "vcp@red.example",
        "Sofía Ramos",
    ),
]


@dataclass(frozen=True)
class UsuarioDemo:
    username: str
    nombre: str
    rol: Rol
    sede: str | None = None


ADMIN = UsuarioDemo("admin", "Administrador", Rol.ADMIN)
PERSONAL = [
    UsuarioDemo("admin.operaciones", "Rosa Medina", Rol.ADMIN),
    UsuarioDemo("bibliotecario.cen", "Lucía Gómez", Rol.BIBLIOTECARIO, "CEN"),
    UsuarioDemo("bibliotecario.norte", "Marcos Ruiz", Rol.BIBLIOTECARIO, "NORTE"),
    UsuarioDemo("bibliotecario.rc", "Paula Sosa", Rol.BIBLIOTECARIO, "SUR_RC"),
    UsuarioDemo("bibliotecario.suplente", "Nora Vega", Rol.BIBLIOTECARIO, "CEN"),
]
BIBLIOTECARIO_VM = UsuarioDemo("bibliotecario.vm", "Hernán Castro", Rol.BIBLIOTECARIO, "VMARIA")


@dataclass(frozen=True)
class SocioDemo:
    documento: str
    nombre: str
    apellido: str
    sede: str
    email: str | None = None
    telefono: str | None = None
    nacimiento: str | None = None
    cuenta: str | None = None


SOCIOS = [
    SocioDemo(
        "30111222",
        "Carla",
        "Soto",
        "CEN",
        "carla.soto@example.com",
        "+543515551111",
        "1985-03-14",
        cuenta="socio.demo",
    ),
    SocioDemo(
        "28555666",
        "Martín",
        "Ríos",
        "NORTE",
        "martin.rios@example.com",
        None,
        "1980-07-02",
        cuenta="martin.rios",
    ),
    SocioDemo("35222333", "Sofía", "Herrera", "SUR_RC", None, "+543584442222", "1991-11-23"),
    SocioDemo(
        "27444555",
        "Diego",
        "Luna",
        "CEN",
        "diego.luna@example.com",
        None,
        "1979-01-30",
        cuenta="diego.luna",
    ),
    SocioDemo(
        "31777888", "Julián", "Ortiz", "SUR_RC", "julian.ortiz@example.com", None, "1986-05-17"
    ),
    SocioDemo(
        "33666777",
        "Valentina",
        "Paz",
        "NORTE",
        "valentina.paz@example.com",
        "+543514443333",
        "1989-09-09",
    ),
    SocioDemo(
        "36888999",
        "Camila",
        "Ferreyra",
        "CEN",
        "camila.ferreyra@example.com",
        None,
        "1994-12-01",
        cuenta="camila.ferreyra",
    ),
    SocioDemo("29333444", "Elena", "Morales", "CEN", None, "+543514998877", "1948-04-21"),
    SocioDemo(
        "32444555", "Pedro", "Acosta", "NORTE", "pedro.acosta@example.com", None, "1988-02-11"
    ),
    SocioDemo(
        "34555666",
        "Ana",
        "Quiroga",
        "SUR_RC",
        "ana.quiroga@example.com",
        None,
        "1990-06-28",
        cuenta="ana.quiroga",
    ),
    SocioDemo(
        "37666777", "Rocío", "Juárez", "NORTE", "rocio.juarez@example.com", None, "1996-10-05"
    ),
    SocioDemo(
        "38777888", "Gonzalo", "Ibáñez", "CEN", "gonzalo.ibanez@example.com", None, "1993-08-19"
    ),
    SocioDemo(
        "39888999", "Lucas", "Bianchi", "VMARIA", "lucas.bianchi@example.com", None, "1999-03-03"
    ),
    SocioDemo(
        "40111333",
        "Tomás",
        "Vera",
        "VMARIA",
        "tomas.vera@example.com",
        "+543534111222",
        "2001-01-15",
        cuenta="tomas.vera",
    ),
]


@dataclass(frozen=True)
class LibroDemo:
    codigo: str  # parte del código de inventario: SEDE-<codigo>-n
    isbn: str | None
    titulo: str
    autores: list[str]
    editorial: str
    anio: int
    categoria: str
    ejemplares: dict[str, int] = field(default_factory=dict)
    tipo: TipoMaterial = TipoMaterial.LIBRO


LIBROS = [
    LibroDemo(
        "705783",
        "9789500705783",
        "Rayuela",
        ["Julio Cortázar"],
        "Sudamericana",
        1963,
        "Literatura argentina",
        {"CEN": 2, "NORTE": 1},
    ),
    LibroDemo(
        "801233",
        "9789875801233",
        "Ficciones",
        ["Jorge Luis Borges"],
        "Emecé",
        1944,
        "Literatura argentina",
        {"CEN": 1, "SUR_RC": 1},
    ),
    LibroDemo(
        "912347",
        "9789504912347",
        "El túnel",
        ["Ernesto Sabato"],
        "Seix Barral",
        1948,
        "Literatura argentina",
        {"NORTE": 2},
    ),
    LibroDemo(
        "384567",
        "9789877384567",
        "Cien años de soledad",
        ["Gabriel García Márquez"],
        "Sudamericana",
        1967,
        "Literatura latinoamericana",
        {"CEN": 1, "NORTE": 1, "SUR_RC": 1},
    ),
    LibroDemo(
        "443214",
        "9789506443214",
        "Facundo",
        ["Domingo Faustino Sarmiento"],
        "Losada",
        1845,
        "Historia",
        {"SUR_RC": 1},
    ),
    LibroDemo(
        "045676",
        "9789874045676",
        "Martín Fierro",
        ["José Hernández"],
        "Colihue",
        1872,
        "Literatura argentina",
        {"CEN": 1},
    ),
    LibroDemo(
        "728895",
        "9789503728895",
        "Las venas abiertas de América Latina",
        ["Eduardo Galeano"],
        "Siglo XXI",
        1971,
        "Ciencias sociales",
        {"NORTE": 1},
    ),
    LibroDemo(
        "350884",
        "9780132350884",
        "Clean Code",
        ["Robert C. Martin"],
        "Prentice Hall",
        2008,
        "Tecnología e informática",
        {"CEN": 1},
    ),
    LibroDemo(
        "777001",
        "9789875777002",
        "El Aleph",
        ["Jorge Luis Borges"],
        "Emecé",
        1949,
        "Literatura argentina",
        {"CEN": 1},
    ),
    LibroDemo(
        "633610",
        "9780201633610",
        "Design Patterns",
        ["Erich Gamma", "Richard Helm", "Ralph Johnson", "John Vlissides"],
        "Addison-Wesley",
        1994,
        "Tecnología e informática",
        {"CEN": 1, "SUR_RC": 1},
    ),
    LibroDemo(
        "670155",
        "9788467041897",
        "Diccionario de la lengua española",
        ["Real Academia Española"],
        "Espasa",
        2014,
        "Obras de referencia",
        {"CEN": 1},
        TipoMaterial.OBRA_DE_REFERENCIA,
    ),
    LibroDemo(
        "498381",
        "9789878498386",
        "El principito",
        ["Antoine de Saint-Exupéry"],
        "Salamandra",
        1943,
        "Infantil y juvenil",
        {"CEN": 1, "NORTE": 1},
    ),
    LibroDemo(
        "992921",
        "9789877992922",
        "Sapiens",
        ["Yuval Noah Harari"],
        "Debate",
        2014,
        "Historia",
        {"SUR_RC": 1},
    ),
    LibroDemo(
        "336621",
        "9789504936626",
        "Cosmos",
        ["Carl Sagan"],
        "Planeta",
        1980,
        "Ciencias naturales",
        {"NORTE": 2, "CEN": 1},
    ),
]
# Ejemplares que llegan a Villa María cuando reabre (una sede con ejemplares no se da de baja).
EJEMPLARES_VM = {"777001": 1, "498381": 1, "992921": 1}

BUENO, REGULAR, DANADO = EstadoFisico.BUENO, EstadoFisico.REGULAR, EstadoFisico.DANADO
ENVIO, TRASLADO = MotivoRemito.ENVIO, MotivoRemito.TRASLADO


def codigo_ejemplar(sede: str, libro: str, n: int) -> str:
    return f"{sede.replace('_', '')}-{libro}-{n}"


def _franjas(sabado: bool) -> list[FranjaHoraria]:
    """Lunes a viernes de 9 a 13 y de 15 a 19; sábado de 9 a 13 (si abre)."""
    franjas = []
    for dia in range(1, 6):
        franjas += [FranjaHoraria(dia, time(9), time(13)), FranjaHoraria(dia, time(15), time(19))]
    if sabado:
        franjas.append(FranjaHoraria(6, time(9), time(13)))
    return franjas


# --- la historia ----------------------------------------------------------------------------

CARLA, MARTIN, SOFIA, DIEGO = "30111222", "28555666", "35222333", "27444555"
JULIAN, VALENTINA, CAMILA, ELENA = "31777888", "33666777", "36888999", "29333444"
PEDRO, ANA, ROCIO, GONZALO = "32444555", "34555666", "37666777", "38777888"
LUCAS, TOMAS = "39888999", "40111333"


def ej(sede: str, libro: str, n: int = 1) -> str:
    return codigo_ejemplar(sede, libro, n)


class Historia:
    """Carga la red de demostración en orden cronológico (cada paso, en su día y hora)."""

    def __init__(self, sesion: Session, clave: str) -> None:
        self.d = Demo(sesion)
        self.sesion = sesion
        self.clave = clave
        self.sede_ids: dict[str, int] = {}
        self.libros: dict[str, int] = {}
        self.p: dict[str, int] = {}  # préstamos por nombre de escena

    # --- utilidades -----------------------------------------------------------------------

    def en(self, dias: int, hora: int = 11, minuto: int = 0) -> None:
        """Ubica el reloj hace ``dias`` días, a la ``hora`` indicada."""
        self.d.reloj.hace(dias, hora, minuto)

    def u(self, username: str) -> Usuario:
        return self.d.usuario(username)

    def datos_sede(self, s: SedeDemo, telefono: str | None = None) -> DatosSede:
        localidad = self.sesion.scalar(
            select(LocalidadORM.id).where(LocalidadORM.nombre == s.localidad)
        )
        assert localidad is not None, s.localidad
        return DatosSede(
            nombre=s.nombre,
            calle=s.calle,
            numero=s.numero,
            localidad_id=localidad,
            telefono=telefono or s.telefono,
            email=s.email,
            responsable=s.responsable,
            horarios=_franjas(s.sabado),
        )

    def version_sede(self, codigo: str) -> int:
        return self.d.sedes.obtener(self.u("admin"), self.sede_ids[codigo]).sede.version

    def crear_usuario(self, actor: Usuario, datos: UsuarioDemo) -> None:
        self.d.usuarios.crear(
            actor,
            DatosUsuarioNuevo(
                username=datos.username,
                password=self.clave,
                nombre=datos.nombre,
                rol=datos.rol,
                sede_id=self.sede_ids[datos.sede] if datos.sede else None,
            ),
        )

    def datos_socio(self, s: SocioDemo, telefono: str | None = None) -> DatosSocio:
        return DatosSocio(
            tipo_documento=TipoDocumento.DNI,
            nro_documento=s.documento,
            nombre=s.nombre,
            apellido=s.apellido,
            fecha_nacimiento=datetime.fromisoformat(s.nacimiento).date() if s.nacimiento else None,
            email=s.email,
            telefono=telefono or s.telefono,
        )

    def registrar_socio(self, actor: Usuario, s: SocioDemo) -> None:
        socio = self.d.socios.crear(actor, self.datos_socio(s))
        if s.cuenta:
            assert socio.id is not None
            self.d.socios.crear_cuenta(actor, socio.id, s.cuenta, self.clave)

    def alta_ejemplares(self, actor: Usuario, libro: LibroDemo, sede: str, cantidad: int) -> None:
        for n in range(1, cantidad + 1):
            self.d.catalogo.crear_ejemplar(
                actor,
                DatosEjemplarNuevo(
                    libro_id=self.libros[libro.codigo],
                    codigo_inventario=ej(sede, libro.codigo, n),
                    estado_fisico=BUENO,
                ),
            )

    def categoria(self, nombre: str) -> int:
        categorias = self.d.catalogo.categorias(self.u("admin"))
        return next(c.id for c in categorias if c.nombre == nombre)

    def datos_libro(self, libro: LibroDemo, **cambios) -> DatosLibroNuevo:
        valores = {
            "titulo": libro.titulo,
            "autores": libro.autores,
            "categoria_id": self.categoria(libro.categoria),
            "tipo_material": libro.tipo,
            "isbn": libro.isbn,
            "editorial": libro.editorial,
            "anio_edicion": libro.anio,
            "portada_url": portada_de(libro.titulo),
        }
        return DatosLibroNuevo(**(valores | cambios))

    def multas(self, prestamo: str) -> list[int]:
        return [m.id for m in self.d.uow.multas.de_prestamo(self.p[prestamo]) if m.id]

    def retorno_generado(self, codigo: str) -> int:
        remito_id = self.sesion.scalar(
            select(RemitoORM.id)
            .join(DetalleRemitoORM, DetalleRemitoORM.remito_id == RemitoORM.id)
            .where(
                DetalleRemitoORM.ejemplar_id == self.d.ejemplar(codigo),
                RemitoORM.motivo == "RETORNO",
                RemitoORM.estado == "GENERADO",
            )
        )
        assert remito_id is not None, codigo
        return remito_id

    def reserva_disponible(self, socio: str, codigo: str) -> int:
        reserva_id = self.sesion.scalar(
            select(ReservaORM.id).where(
                ReservaORM.socio_id == self.d.socio(socio),
                ReservaORM.ejemplar_id == self.d.ejemplar(codigo),
                ReservaORM.estado == "DISPONIBLE_PARA_RETIRO",
            )
        )
        assert reserva_id is not None, (socio, codigo)
        return reserva_id

    def prestamo_abierto(self, socio: str, codigo: str) -> int:
        prestamo_id = self.sesion.scalar(
            select(PrestamoORM.id).where(
                PrestamoORM.socio_id == self.d.socio(socio),
                PrestamoORM.ejemplar_id == self.d.ejemplar(codigo),
                PrestamoORM.estado == "SOLICITADO",
            )
        )
        assert prestamo_id is not None, (socio, codigo)
        return prestamo_id

    def libro_id(self, codigo: str) -> int:
        return self.libros[codigo]

    # --- la historia ----------------------------------------------------------------------

    def contar(
        self,
        volumen: bool = True,
        dias_de_movimiento: int = 59,
        avisar: Callable[[str], None] = lambda _texto: None,
    ) -> None:
        """Cuenta la historia; con ``volumen`` suma catálogo, socios y movimiento diario."""
        avisar("Fundación de la red: sedes, personal, catálogo y socios...")
        self.fundacion()
        if volumen:
            # Mucho catálogo, más socios y movimiento diario (seed_volumen).
            from app.db.seed_volumen import Volumen

            extra = Volumen(self, avisar)
            avisar("Catálogo amplio y socios nuevos...")
            extra.fundar()
            extra.simular(desde=dias_de_movimiento)
        avisar("Los casos especiales de los últimos 50 días...")
        self.primer_mes()
        self.segundo_mes()
        self.ultimas_dos_semanas()
        self.hoy()

    def _admin(self) -> Usuario:
        """El primer administrador: no hay quién lo dé de alta, se crea directamente."""
        self.sesion.add(
            UsuarioORM(
                username=ADMIN.username,
                password_hash=hashear_clave(self.clave),
                nombre=ADMIN.nombre,
                rol=ADMIN.rol.value,
                activo=True,
            )
        )
        self.sesion.commit()
        return self.u(ADMIN.username)

    def fundacion(self) -> None:
        """Hace 90 a 60 días: sedes, personal, parámetros, catálogo y socios."""
        d = self.d
        self.en(90, 9)
        admin = self._admin()
        for s in SEDES:
            vista = d.sedes.crear(admin, s.codigo, self.datos_sede(s))
            assert vista.sede.id is not None
            self.sede_ids[s.codigo] = vista.sede.id
        self.en(89, 10)
        for datos in PERSONAL:
            self.crear_usuario(admin, datos)
        rosa = self.u("admin.operaciones")
        biblio = {
            "CEN": self.u("bibliotecario.cen"),
            "NORTE": self.u("bibliotecario.norte"),
            "SUR_RC": self.u("bibliotecario.rc"),
        }

        # El administrador activa las multas por daño y por extravío (queda en la auditoría).
        self.en(88, 9)
        d.parametros.actualizar(admin, "multa_por_danio", "3000")
        d.parametros.actualizar(admin, "multa_por_extravio", "15000")

        # Catálogo: el administrador carga los libros; cada sede, sus ejemplares.
        self.en(87, 10)
        for libro in LIBROS:
            creado = d.catalogo.crear_libro(admin, self.datos_libro(libro))
            assert creado.id is not None
            self.libros[libro.codigo] = creado.id
        self.en(86, 10)
        for libro in LIBROS:
            for sede, cantidad in libro.ejemplares.items():
                self.alta_ejemplares(biblio[sede], libro, sede, cantidad)

        # Socios de las sedes abiertas, cada uno registrado en el mostrador de su sede.
        momentos = [
            (85, 10),
            (85, 12),
            (84, 10),
            (84, 12),
            (83, 10),
            (83, 12),
            (82, 10),
            (82, 12),
            (81, 10),
            (81, 11),
            (81, 12),
            (81, 16),
        ]
        socios = [s for s in SOCIOS if s.sede != "VMARIA"]
        for (dias, hora), s in zip(momentos, socios, strict=True):
            self.en(dias, hora)
            self.registrar_socio(biblio[s.sede], s)

        # Villa María cierra por mudanza (todavía no tenía personal ni ejemplares).
        self.en(80, 12)
        d.sedes.dar_de_baja(
            admin,
            self.sede_ids["VMARIA"],
            self.version_sede("VMARIA"),
            "Mudanza a un edificio nuevo",
        )
        # Central cambia de teléfono; se corrige un libro y el estado de un ejemplar.
        self.en(75, 9)
        nuevo = self.datos_sede(SEDES[0], telefono="+543514225678")
        d.sedes.modificar(admin, self.sede_ids["CEN"], self.version_sede("CEN"), nuevo)
        self.en(72, 11)
        facundo = next(lib for lib in LIBROS if lib.codigo == "443214")
        d.catalogo.modificar_libro(
            rosa,
            self.libros["443214"],
            self.datos_libro(
                facundo,
                titulo="Facundo. Civilización y barbarie",
                editorial="Losada (edición crítica)",
            ),
            d.catalogo.obtener_libro(admin, self.libros["443214"]).version,
        )
        self.en(71, 16)
        principito = ej("CEN", "498381")
        d.catalogo.modificar_ejemplar(
            biblio["CEN"],
            d.ejemplar(principito),
            d.version_ejemplar(principito),
            REGULAR,
            "Hojas subrayadas con lápiz",
        )
        self.en(70, 12)
        cosmos2 = ej("NORTE", "336621", 2)
        d.catalogo.dar_de_baja_ejemplar(
            biblio["NORTE"],
            d.ejemplar(cosmos2),
            d.version_ejemplar(cosmos2),
            "Deterioro irreparable por humedad",
        )
        # Villa Carlos Paz cierra por obras.
        self.en(70, 18)
        d.sedes.dar_de_baja(
            rosa,
            self.sede_ids["OESTE_VCP"],
            self.version_sede("OESTE_VCP"),
            "Cierre por obras de ampliación",
        )

        # Villa María reabre: bibliotecario, ejemplares nuevos y sus primeros socios.
        self.en(66, 9)
        d.sedes.reactivar(admin, self.sede_ids["VMARIA"], self.version_sede("VMARIA"))
        self.en(65, 9)
        self.crear_usuario(admin, BIBLIOTECARIO_VM)
        vm = self.u("bibliotecario.vm")
        self.en(64, 10)
        for codigo, cantidad in EJEMPLARES_VM.items():
            libro = next(lib for lib in LIBROS if lib.codigo == codigo)
            self.alta_ejemplares(vm, libro, "VMARIA", cantidad)
        for (dias, hora), s in zip(
            [(64, 12), (63, 10)], [s for s in SOCIOS if s.sede == "VMARIA"], strict=True
        ):
            self.en(dias, hora)
            self.registrar_socio(vm, s)

        # La suplente pasa de Central a Norte; tope de multa; Sofía queda inhabilitada.
        self.en(60, 9)
        suplente = self.u("bibliotecario.suplente")
        assert suplente.id is not None
        d.usuarios.modificar(admin, suplente.id, suplente.nombre, self.sede_ids["NORTE"])
        d.parametros.actualizar(rosa, "multa_tope_por_prestamo", "5000")
        d.socios.inhabilitar(admin, d.socio(SOFIA), "Daño reiterado de material prestado")

    def primer_mes(self) -> None:
        """Hace 50 a 31 días: primeros préstamos y envíos, cambios y bajas de socios."""
        d = self.d
        admin, rosa = self.u("admin"), self.u("admin.operaciones")
        cen, norte, rc, vm = (self.u(f"bibliotecario.{s}") for s in ("cen", "norte", "rc", "vm"))
        martin_datos = next(s for s in SOCIOS if s.documento == MARTIN)

        self.en(50, 10)
        d.socios.modificar(norte, d.socio(MARTIN), self.datos_socio(martin_datos, "+543515557777"))
        self.en(50, 12)
        d.socios.dar_de_baja(
            cen, d.socio(DIEGO), TipoBaja.A_PEDIDO, "Se mudó fuera de la provincia"
        )

        # Martín (Norte) pide «Rayuela» de Central; Central traslada «Clean Code» a Río Cuarto.
        self.en(45)
        self.p["rayuela"] = d.prestar(norte, MARTIN, ej("CEN", "705783"))
        ida = d.enviar(cen, "NORTE", ENVIO, [(ej("CEN", "705783"), self.p["rayuela"])])
        traslado = d.enviar(cen, "SUR_RC", TRASLADO, [(ej("CEN", "350884"), None)])
        self.en(45, 15)
        d.socios.dar_de_baja(
            admin, d.socio(PEDRO), TipoBaja.ADMINISTRATIVA, "Conducta reiterada en sala"
        )
        self.en(43)
        d.recibir(norte, ida, d.linea(ej("CEN", "705783"), BUENO))
        d.prestamos.entregar(norte, self.p["rayuela"])
        self.en(41)
        d.recibir(rc, traslado, d.linea(ej("CEN", "350884"), BUENO))

        # Camila (Central) pide «El túnel» de Norte.
        self.en(40)
        self.p["tunel"] = d.prestar(cen, CAMILA, ej("NORTE", "912347"))
        ida = d.enviar(norte, "CEN", ENVIO, [(ej("NORTE", "912347"), self.p["tunel"])])
        self.en(40, 14)
        d.socios.dar_de_baja(rc, d.socio(ANA), TipoBaja.A_PEDIDO, "Viaja al exterior por un año")
        d.socios.inhabilitar(rosa, d.socio(LUCAS), "Documentación de domicilio pendiente")
        self.en(37)
        d.recibir(cen, ida, d.linea(ej("NORTE", "912347"), BUENO))
        d.prestamos.entregar(cen, self.p["tunel"])

        # Carla se lleva «Cien años de soledad» en Central (préstamo local).
        self.en(35)
        self.p["cien"] = d.prestar(cen, CARLA, ej("CEN", "384567"))
        d.prestamos.entregar(cen, self.p["cien"])
        self.en(35, 16)
        d.socios.dar_de_baja(
            admin, d.socio(ELENA), TipoBaja.FALLECIMIENTO, "Informado por la familia"
        )
        self.en(33)
        d.socios.rehabilitar(rosa, d.socio(LUCAS))
        self.en(32)
        self.p["sapiens_lucas"] = d.prestar(vm, LUCAS, ej("VMARIA", "992921"))
        d.prestamos.entregar(vm, self.p["sapiens_lucas"])

    def segundo_mes(self) -> None:
        """Hace 30 a 13 días: envíos con problemas, devoluciones, multas, pagos y reservas."""
        d = self.d
        admin, rosa = self.u("admin"), self.u("admin.operaciones")
        cen, norte, rc, vm = (self.u(f"bibliotecario.{s}") for s in ("cen", "norte", "rc", "vm"))
        tomas_u, carla_u, camila_u = (
            self.u("tomas.vera"),
            self.u("socio.demo"),
            self.u("camila.ferreyra"),
        )

        # Julián (Río Cuarto) pide «Ficciones» de Central; el administrador presta en Villa María.
        self.en(30)
        self.p["ficciones"] = d.prestar(rc, JULIAN, ej("CEN", "801233"))
        ida_ficciones = d.enviar(cen, "SUR_RC", ENVIO, [(ej("CEN", "801233"), self.p["ficciones"])])
        self.p["principito_tomas"] = d.prestar(admin, TOMAS, ej("VMARIA", "498381"), "VMARIA")
        d.prestamos.entregar(admin, self.p["principito_tomas"])
        d.parametros.actualizar(admin, "renovaciones_maximas", "2")
        self.en(29, 9)
        d.parametros.actualizar(rosa, "renovaciones_maximas", "1")
        # «Ficciones» llega mojado: el préstamo se cancela y se genera el retorno a Central.
        self.en(28)
        d.recibir(rc, ida_ficciones, d.linea(ej("CEN", "801233"), DANADO, "Llegó mojado"))
        self.p["cosmos_rocio"] = d.prestar(norte, ROCIO, ej("NORTE", "336621"))
        d.prestamos.entregar(norte, self.p["cosmos_rocio"])
        retorno_ficciones = self.retorno_generado(ej("CEN", "801233"))
        self.en(26)
        d.remitos.empaquetar(rc, retorno_ficciones)
        d.remitos.despachar(rc, retorno_ficciones)
        anulado = d.generar(cen, "SUR_RC", TRASLADO, [(ej("CEN", "633610"), None)])
        self.en(25, 9)
        d.remitos.anular(cen, anulado, "Se decidió conservarlo en Central")
        # Martín devuelve «Rayuela» en término: vuelve a Central con un remito de retorno.
        self.en(25)
        devuelto = d.devoluciones.registrar(norte, self.p["rayuela"], EstadoRecibido.BUENO)
        assert devuelto.remito_retorno is not None and devuelto.remito_retorno.id is not None
        retorno_rayuela = devuelto.remito_retorno.id
        d.remitos.empaquetar(norte, retorno_rayuela)
        d.remitos.despachar(norte, retorno_rayuela)
        self.en(24)
        d.recibir(cen, retorno_ficciones, d.linea(ej("CEN", "801233"), DANADO, "Sigue húmedo"))
        self.en(23)
        d.recibir(cen, retorno_rayuela, d.linea(ej("CEN", "705783"), BUENO))
        # Ana pide volver desde su cuenta; Río Cuarto envía «Design Patterns» a Central.
        self.en(22)
        d.socios.solicitar_reactivacion(
            self.u("ana.quiroga"), d.socio(ANA), "Volví antes de lo previsto"
        )
        destruido = d.enviar(rc, "CEN", TRASLADO, [(ej("SUR_RC", "633610"), None)])
        # Gonzalo se lleva «Cosmos» de Central y no lo devuelve.
        self.en(21)
        self.p["cosmos_gonzalo"] = d.prestar(cen, GONZALO, ej("CEN", "336621"))
        d.prestamos.entregar(cen, self.p["cosmos_gonzalo"])
        # Llega destruido; el administrador rechaza la solicitud de Ana.
        self.en(20, 10)
        d.recibir(
            cen,
            destruido,
            d.linea(
                ej("SUR_RC", "633610"), DANADO, "Caja aplastada en el transporte", destruido=True
            ),
        )
        d.socios.rechazar_solicitud(
            admin, d.socio(ANA), "Debe presentar un comprobante de domicilio actualizado"
        )
        # Julián retira «Facundo» en Río Cuarto y no lo devuelve; Valentina pide «Rayuela».
        self.en(20)
        self.p["facundo"] = d.prestar(rc, JULIAN, ej("SUR_RC", "443214"))
        d.prestamos.entregar(rc, self.p["facundo"])
        self.p["rayuela2"] = d.prestar(norte, VALENTINA, ej("CEN", "705783"))
        ida_rayuela2 = d.enviar(cen, "NORTE", ENVIO, [(ej("CEN", "705783"), self.p["rayuela2"])])
        # Carla devuelve dos días tarde: multa de $400 que paga con débito al día siguiente.
        self.en(19, 17)
        d.devoluciones.registrar(cen, self.p["cien"], EstadoRecibido.REGULAR, "Tapa gastada")
        self.en(18)
        d.recibir(norte, ida_rayuela2, d.linea(ej("CEN", "705783"), BUENO))
        d.prestamos.entregar(norte, self.p["rayuela2"])
        self.en(18, 12)
        (multa_carla,) = self.multas("cien")
        d.pagos.saldar_en_mostrador(cen, multa_carla, MedioPago.DEBITO, "Cupón 004512")
        # Rocío informa que perdió «Cosmos»: baja del ejemplar y multa por extravío.
        self.en(18, 16)
        d.devoluciones.registrar(
            norte, self.p["cosmos_rocio"], EstadoRecibido.EXTRAVIADO, "Lo perdió en una mudanza"
        )
        # Central traslada a Villa María el diccionario y una «Rayuela».
        self.en(16, 9)
        incompleto = d.enviar(
            cen,
            "VMARIA",
            TRASLADO,
            [(ej("CEN", "670155"), None), (ej("CEN", "705783", 2), None)],
        )
        # Tomás devuelve «El principito» dañado el día del vencimiento: multa por daño.
        self.en(16, 12)
        d.devoluciones.registrar(
            vm, self.p["principito_tomas"], EstadoRecibido.DANADO, "Tapa desprendida"
        )
        # Lucas había dejado «Sapiens» en el buzón el sábado: se registra con la fecha real.
        self.en(15, 9)
        buzon = datetime.combine(
            d.reloj.hoy() - timedelta(days=3), time(18), d.reloj.ahora_local().tzinfo
        )
        d.devoluciones.registrar(
            vm,
            self.p["sapiens_lucas"],
            EstadoRecibido.BUENO,
            fecha_hora=buzon,
            motivo_fecha="Lo dejó en el buzón de la sede durante el fin de semana",
        )
        d.socios.reactivar(admin, d.socio(PEDRO))
        # Tomás paga en línea: la tarjeta de prueba terminada en 0002 se rechaza; reintenta.
        self.en(15, 10)
        (multa_tomas,) = self.multas("principito_tomas")
        pago = d.pagos.iniciar_en_linea(tomas_u, multa_tomas)
        assert pago.id is not None
        d.pagos.pagar_en_linea(tomas_u, pago.id, FormaEnLinea.TARJETA_CREDITO, "0002")
        pago = d.pagos.iniciar_en_linea(tomas_u, multa_tomas)
        assert pago.id is not None
        d.pagos.pagar_en_linea(tomas_u, pago.id, FormaEnLinea.TARJETA_DEBITO, "4242")
        # Norte manda «El túnel» (2) a Río Cuarto y el envío nunca llega.
        self.en(15)
        self.perdido = d.enviar(norte, "SUR_RC", TRASLADO, [(ej("NORTE", "912347", 2), None)])
        # Carla reserva «Facundo» desde su cuenta (el único ejemplar está con Julián).
        self.en(15, 12)
        reserva = d.reservas.reservar(carla_u, self.libro_id("443214"), self.sede_ids["CEN"])
        assert reserva.id is not None
        self.reserva_carla = reserva.id
        # Villa María recibe el traslado: la «Rayuela» no venía en la caja.
        self.en(14, 10)
        d.recibir(
            vm,
            incompleto,
            d.linea(ej("CEN", "670155"), BUENO),
            d.linea(ej("CEN", "705783", 2), None, "No venía en la caja", faltante=True),
        )
        # Pedro reserva «Cosmos»: no queda ninguno disponible en la red.
        self.en(14, 12)
        d.reservas.reservar(norte, self.libro_id("336621"), self.sede_ids["NORTE"], d.socio(PEDRO))
        # Camila pide «El principito» desde su cuenta y al día siguiente se arrepiente.
        self.en(14, 18)
        solicitud = d.prestamos.solicitar(camila_u, self.libro_id("498381"), self.sede_ids["CEN"])
        assert solicitud.id is not None
        self.en(13, 9)
        d.prestamos.cancelar(camila_u, solicitud.id, "Lo conseguí prestado de una amiga")

    def ultimas_dos_semanas(self) -> None:
        """Hace 12 a 1 días: retornos, reservas, autogestión, renovación y pagos."""
        d = self.d
        admin = self.u("admin")
        cen, norte, rc, vm = (self.u(f"bibliotecario.{s}") for s in ("cen", "norte", "rc", "vm"))
        camila_u, carla_u, martin_u = (
            self.u("camila.ferreyra"),
            self.u("socio.demo"),
            self.u("martin.rios"),
        )

        # Camila devuelve cuatro días tarde: multa y retorno a Norte.
        self.en(12)
        devuelto = d.devoluciones.registrar(cen, self.p["tunel"], EstadoRecibido.BUENO)
        assert devuelto.remito_retorno is not None and devuelto.remito_retorno.id is not None
        retorno_tunel = devuelto.remito_retorno.id
        self.en(12, 15)
        d.catalogo.reparar_ejemplar(
            vm, d.ejemplar(ej("VMARIA", "498381")), d.version_ejemplar(ej("VMARIA", "498381"))
        )
        # Valentina reserva «El túnel» (los dos ejemplares están fuera); Tomás se lleva «Sapiens».
        self.en(11)
        d.reservas.reservar(
            norte, self.libro_id("912347"), self.sede_ids["NORTE"], d.socio(VALENTINA)
        )
        self.p["sapiens_tomas"] = d.prestar(vm, TOMAS, ej("VMARIA", "992921"))
        d.prestamos.entregar(vm, self.p["sapiens_tomas"])
        # Martín se lleva «Las venas abiertas»; Central repara «Ficciones».
        self.en(10)
        self.p["venas"] = d.prestar(norte, MARTIN, ej("NORTE", "728895"))
        d.prestamos.entregar(norte, self.p["venas"])
        d.catalogo.reparar_ejemplar(
            cen, d.ejemplar(ej("CEN", "801233")), d.version_ejemplar(ej("CEN", "801233"))
        )
        self.en(10, 12)
        d.reservas.cancelar(carla_u, self.reserva_carla, "Lo consiguió en otra biblioteca")
        # Camila empieza a pagar su multa en línea y abandona el pago.
        self.en(10, 20)
        (multa_camila,) = self.multas("tunel")
        d.pagos.iniciar_en_linea(camila_u, multa_camila)
        # Pedro reserva «Las venas abiertas»; Valentina pide «El principito» y no lo retira.
        self.en(9)
        d.reservas.reservar(norte, self.libro_id("728895"), self.sede_ids["NORTE"], d.socio(PEDRO))
        d.prestar(norte, VALENTINA, ej("NORTE", "498381"))
        # Martín devuelve «Las venas» y queda para Pedro; aparece el «Cosmos» de Rocío y también
        # queda para Pedro.
        self.en(8, 10)
        d.devoluciones.registrar(norte, self.p["venas"], EstadoRecibido.BUENO)
        cosmos = ej("NORTE", "336621")
        self.en(8, 15)
        d.catalogo.recuperar_ejemplar(
            norte,
            d.ejemplar(cosmos),
            d.version_ejemplar(cosmos),
            REGULAR,
            "La socia lo encontró y lo trajo",
        )
        self.en(8, 17)
        reserva_tomas = d.reservas.reservar(
            vm, self.libro_id("443214"), self.sede_ids["VMARIA"], d.socio(TOMAS)
        )
        assert reserva_tomas.id is not None
        # Pedro retira «Cosmos» (cumple su reserva).
        self.en(7)
        d.reservas.retirar(norte, self.reserva_disponible(PEDRO, cosmos))
        # Aparece la «Rayuela» que faltó en el traslado; Diego pide volver; Lucas reserva.
        self.en(6, 10)
        rayuela2 = ej("CEN", "705783", 2)
        d.catalogo.recuperar_ejemplar(
            cen,
            d.ejemplar(rayuela2),
            d.version_ejemplar(rayuela2),
            BUENO,
            "Apareció en el depósito de Central",
        )
        d.socios.solicitar_reactivacion(
            self.u("diego.luna"), d.socio(DIEGO), "Volví a vivir en Córdoba"
        )
        d.reservas.reservar(vm, self.libro_id("443214"), self.sede_ids["VMARIA"], d.socio(LUCAS))
        # El administrador cancela una reserva duplicada (opera en cualquier sede).
        self.en(5, 9)
        d.reservas.cancelar(admin, reserva_tomas.id, "Reserva duplicada por error")
        # Carla pide «Cien años de soledad» de Norte.
        self.en(5)
        self.p["cien2"] = d.prestar(cen, CARLA, ej("NORTE", "384567"))
        # Tareas de la madrugada: el retiro de Valentina venció.
        self.en(4, 0, 5)
        d.prestamos.vencer_retiros()
        # Martín pide «El Aleph» desde su cuenta: el sistema lo trae de Central.
        self.en(4, 10)
        d.prestamos.solicitar(martin_u, self.libro_id("777001"), self.sede_ids["NORTE"])
        # Madrugada: la reserva de «Las venas» de Pedro venció sin retirar.
        self.en(3, 0, 5)
        d.reservas.vencer_reservas()
        # Envíos: Norte manda «Cien años»; Central despacha el retorno de «El túnel»; Villa
        # María traslada «El Aleph» a Central.
        self.en(3)
        d.enviar(norte, "CEN", ENVIO, [(ej("NORTE", "384567"), self.p["cien2"])])
        d.remitos.empaquetar(cen, retorno_tunel)
        d.remitos.despachar(cen, retorno_tunel)
        en_viaje = d.enviar(vm, "CEN", TRASLADO, [(ej("VMARIA", "777001"), None)])
        self.en(2, 9)
        d.remitos.pasar_a_transito(vm, en_viaje)
        d.recibir(norte, retorno_tunel, d.linea(ej("NORTE", "912347"), BUENO))
        empaquetado = d.generar(
            rc, "VMARIA", TRASLADO, [(ej("SUR_RC", "992921"), None)], "Refuerzo para Villa María"
        )
        d.remitos.empaquetar(rc, empaquetado)
        # Carla se lleva «Martín Fierro»; Martín lo reserva para retirar en Norte.
        self.en(2)
        self.p["fierro"] = d.prestar(cen, CARLA, ej("CEN", "045676"))
        d.prestamos.entregar(cen, self.p["fierro"])
        d.reservas.reservar(martin_u, self.libro_id("045676"), self.sede_ids["NORTE"])
        # Valentina devuelve «Rayuela» dañada: multa por daño y retorno a Central.
        self.en(2, 16)
        d.devoluciones.registrar(
            norte, self.p["rayuela2"], EstadoRecibido.DANADO, "Lomo despegado y hojas sueltas"
        )
        self.en(1, 10)
        (multa_valentina,) = self.multas("rayuela2")
        d.pagos.saldar_en_mostrador(norte, multa_valentina, MedioPago.EFECTIVO, None)
        d.prestamos.renovar(vm, self.p["sapiens_tomas"])
        # Norte despacha a Central la «Rayuela» que Valentina devolvió dañada.
        self.en(1, 14)
        self.retorno_rayuela2 = self.retorno_generado(ej("CEN", "705783"))
        d.remitos.empaquetar(norte, self.retorno_rayuela2)
        d.remitos.despachar(norte, self.retorno_rayuela2)
        # Carla devuelve «Martín Fierro»: la reserva de Martín se cumple con un envío a Norte.
        self.en(1, 12)
        d.devoluciones.registrar(cen, self.p["fierro"], EstadoRecibido.BUENO)
        self.p["fierro_martin"] = self.prestamo_abierto(MARTIN, ej("CEN", "045676"))
        # Carla pide «El principito» desde su cuenta para retirar en Central.
        self.en(1, 17)
        d.prestamos.solicitar(carla_u, self.libro_id("498381"), self.sede_ids["CEN"])

    def hoy(self) -> None:
        """Hoy: vencidos, un envío perdido, el cobro de Camila, cierres y la baja de la suplente."""
        d = self.d
        admin, rosa, cen = self.u("admin"), self.u("admin.operaciones"), self.u("bibliotecario.cen")
        self.en(0, 0, 5)
        d.prestamos.detectar_vencidos()
        self.en(0, 8)
        suplente = self.u("bibliotecario.suplente")
        assert suplente.id is not None
        d.usuarios.dar_de_baja(admin, suplente.id)
        d.remitos.marcar_extraviado(admin, self.perdido, "Superó el plazo de tránsito sin llegar")
        # Central recibe la «Rayuela» dañada: queda en revisión hasta que se repare.
        d.recibir(cen, self.retorno_rayuela2, d.linea(ej("CEN", "705783"), DANADO, "Hojas sueltas"))
        # Central arma el envío de «Martín Fierro» para Martín (queda generado).
        d.generar(cen, "NORTE", ENVIO, [(ej("CEN", "045676"), self.p["fierro_martin"])])
        # Camila paga en el mostrador: el pago en línea que había dejado queda cancelado.
        (multa_camila,) = self.multas("tunel")
        d.pagos.saldar_en_mostrador(cen, multa_camila, MedioPago.TRANSFERENCIA, "Op. 77120943")
        # Cierres por fecha: un feriado en Central, inventario en Norte y una capacitación que
        # se suspende.
        hoy = d.reloj.hoy()
        d.sedes.agregar_excepciones(
            admin,
            self.sede_ids["CEN"],
            DatosExcepcion(
                hoy + timedelta(days=12),
                None,
                TipoExcepcion.CIERRE_TOTAL,
                motivo="Feriado provincial",
            ),
        )
        d.sedes.agregar_excepciones(
            admin,
            self.sede_ids["NORTE"],
            DatosExcepcion(
                hoy + timedelta(days=20),
                hoy + timedelta(days=21),
                TipoExcepcion.CIERRE_TOTAL,
                motivo="Inventario anual",
            ),
        )
        (capacitacion,) = d.sedes.agregar_excepciones(
            rosa,
            self.sede_ids["NORTE"],
            DatosExcepcion(
                hoy + timedelta(days=5),
                None,
                TipoExcepcion.CIERRE_PARCIAL,
                time(15),
                time(19),
                "Capacitación del personal",
            ),
        )
        d.sedes.agregar_excepciones(
            rosa,
            self.sede_ids["CEN"],
            DatosExcepcion(
                hoy + timedelta(days=3),
                None,
                TipoExcepcion.CIERRE_PARCIAL,
                time(15),
                time(19),
                "Reunión de personal",
            ),
        )
        assert capacitacion.id is not None
        d.sedes.quitar_excepcion(admin, self.sede_ids["NORTE"], capacitacion.id)
