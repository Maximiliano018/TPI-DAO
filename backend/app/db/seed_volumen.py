# ruff: noqa: E501
"""Volumen de demostración: mucho catálogo, muchos socios y dos meses de movimiento diario.

La historia de ``seed_historia`` cuenta a mano los casos especiales; este módulo le suma volumen
para que las pantallas y los reportes se vean como en una red real:

* **Catálogo:** más de 120 libros (clásicos universales, autores argentinos y latinoamericanos,
  los más leídos de los últimos años, infantiles, ciencia, historia, filosofía e informática),
  con dos revistas y dos obras de referencia, y sus ejemplares repartidos en las sedes activas.
* **Socios:** 72 socios más, registrados en el mostrador de cada sede.
* **Movimiento:** día por día, de hace 59 días a ayer: préstamos locales y entre sedes, envíos,
  despachos y recepciones (algunas con daño), retornos, traslados entre sedes, renovaciones,
  devoluciones en término, tardías, dañadas y extraviadas, reservas que se asignan, se retiran o
  vencen, y multas que se pagan en el mostrador o quedan pendientes.

Todo pasa por los casos de uso reales (con el reloj de ``seed_demo``), así cada dato nace con
su historial y respeta las reglas de negocio: si una acción no corresponde (un socio
inhabilitado, el máximo de préstamos, un libro repetido), el caso de uso la rechaza y la
simulación sigue con la próxima. El azar usa una semilla fija: la demo sale siempre igual.

Los ISBN de estos libros son de demostración (válidos, pero no los de una edición real).
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.db.models import (
    DetalleRemitoORM,
    EjemplarORM,
    MultaORM,
    PrestamoORM,
    RemitoORM,
    ReservaORM,
    SocioORM,
)
from app.db.portadas_demo import portada_de
from app.exceptions import ErrorDeNegocio
from app.models.devolucion import EstadoRecibido
from app.models.ejemplar import EstadoFisico
from app.models.libro import TipoMaterial
from app.models.pago import MedioPago
from app.models.remito import MotivoRemito, RecepcionLinea
from app.models.socio import TipoDocumento
from app.models.usuario import Usuario
from app.services.catalogo_service import DatosEjemplarNuevo, DatosLibroNuevo
from app.services.remito_service import LineaNueva
from app.services.socio_service import DatosSocio

if TYPE_CHECKING:
    from app.db.seed_historia import Historia

LIT_AR, LIT_LA, LIT_UNI = (
    "Literatura argentina",
    "Literatura latinoamericana",
    "Literatura universal",
)
INFANTIL, HISTORIA, SOCIALES = "Infantil y juvenil", "Historia", "Ciencias sociales"
NATURALES, TECNO, ARTE = "Ciencias naturales", "Tecnología e informática", "Arte y música"
FILOSOFIA, REFERENCIA = "Filosofía", "Obras de referencia"
REVISTA, OBRA_REF = TipoMaterial.REVISTA, TipoMaterial.OBRA_DE_REFERENCIA


@dataclass(frozen=True)
class LibroVolumen:
    titulo: str
    autores: tuple[str, ...]
    editorial: str
    anio: int
    categoria: str
    tipo: TipoMaterial = TipoMaterial.LIBRO
    popular: bool = False  # más pedido: más ejemplares y más préstamos


def _l(
    titulo: str,
    autores: str,
    editorial: str,
    anio: int,
    categoria: str,
    tipo: TipoMaterial = TipoMaterial.LIBRO,
    popular: bool = False,
) -> LibroVolumen:
    return LibroVolumen(
        titulo, tuple(autores.split("; ")), editorial, anio, categoria, tipo, popular
    )


# Clásicos y más leídos (referencias: listas de clásicos universales y rankings de lectura de
# Argentina 2024-2025). El año es el de la edición que tiene la red.
LIBROS_VOLUMEN = [
    # --- literatura argentina ---
    _l("El Eternauta", "Héctor G. Oesterheld; Francisco Solano López", "Doedytores", 2015, LIT_AR, popular=True),
    _l("Sobre héroes y tumbas", "Ernesto Sabato", "Seix Barral", 2011, LIT_AR),
    _l("La invención de Morel", "Adolfo Bioy Casares", "Emecé", 2009, LIT_AR),
    _l("Los siete locos", "Roberto Arlt", "Losada", 2008, LIT_AR),
    _l("El juguete rabioso", "Roberto Arlt", "Losada", 2010, LIT_AR),
    _l("Boquitas pintadas", "Manuel Puig", "Seix Barral", 2012, LIT_AR),
    _l("El beso de la mujer araña", "Manuel Puig", "Seix Barral", 2013, LIT_AR),
    _l("Respiración artificial", "Ricardo Piglia", "Anagrama", 2001, LIT_AR),
    _l("El entenado", "Juan José Saer", "Seix Barral", 2013, LIT_AR),
    _l("Operación masacre", "Rodolfo Walsh", "De la Flor", 2010, LIT_AR),
    _l("Cuentos de amor de locura y de muerte", "Horacio Quiroga", "Losada", 2005, LIT_AR),
    _l("Bestiario", "Julio Cortázar", "Alfaguara", 2014, LIT_AR),
    _l("Historias de cronopios y de famas", "Julio Cortázar", "Alfaguara", 2013, LIT_AR),
    _l("El libro de arena", "Jorge Luis Borges", "Emecé", 2011, LIT_AR),
    _l("Las cosas que perdimos en el fuego", "Mariana Enriquez", "Anagrama", 2016, LIT_AR, popular=True),
    _l("Nuestra parte de noche", "Mariana Enriquez", "Anagrama", 2019, LIT_AR, popular=True),
    _l("Distancia de rescate", "Samanta Schweblin", "Random House", 2014, LIT_AR),
    _l("Kentukis", "Samanta Schweblin", "Random House", 2018, LIT_AR),
    _l("Las viudas de los jueves", "Claudia Piñeiro", "Alfaguara", 2005, LIT_AR),
    _l("Elena sabe", "Claudia Piñeiro", "Alfaguara", 2006, LIT_AR),
    _l("Crímenes imperceptibles", "Guillermo Martínez", "Destino", 2003, LIT_AR),
    _l("La pregunta de sus ojos", "Eduardo Sacheri", "Galerna", 2005, LIT_AR),
    _l("Papeles en el viento", "Eduardo Sacheri", "Alfaguara", 2011, LIT_AR),
    _l("Las aventuras de la China Iron", "Gabriela Cabezón Cámara", "Random House", 2017, LIT_AR),
    _l("Don Segundo Sombra", "Ricardo Güiraldes", "Losada", 2005, LIT_AR),
    _l("Adán Buenosayres", "Leopoldo Marechal", "Sudamericana", 2013, LIT_AR),
    # --- literatura latinoamericana ---
    _l("El amor en los tiempos del cólera", "Gabriel García Márquez", "Random House", 2015, LIT_LA),
    _l("Crónica de una muerte anunciada", "Gabriel García Márquez", "Random House", 2014, LIT_LA, popular=True),
    _l("La ciudad y los perros", "Mario Vargas Llosa", "Alfaguara", 2012, LIT_LA),
    _l("La casa de los espíritus", "Isabel Allende", "Sudamericana", 2012, LIT_LA),
    _l("Pedro Páramo", "Juan Rulfo", "RM", 2005, LIT_LA),
    _l("Veinte poemas de amor y una canción desesperada", "Pablo Neruda", "Seix Barral", 2009, LIT_LA),
    _l("2666", "Roberto Bolaño", "Anagrama", 2004, LIT_LA),
    _l("La tregua", "Mario Benedetti", "Sudamericana", 2015, LIT_LA),
    _l("Como agua para chocolate", "Laura Esquivel", "Debolsillo", 2016, LIT_LA),
    _l("El laberinto de la soledad", "Octavio Paz", "Fondo de Cultura Económica", 2015, LIT_LA),
    _l("Aura", "Carlos Fuentes", "Era", 2014, LIT_LA),
    _l("Los ríos profundos", "José María Arguedas", "Losada", 2005, LIT_LA),
    # --- literatura universal ---
    _l("Odisea", "Homero", "Gredos", 2014, LIT_UNI),
    _l("Don Quijote de la Mancha", "Miguel de Cervantes", "Alfaguara", 2015, LIT_UNI, popular=True),
    _l("La divina comedia", "Dante Alighieri", "Cátedra", 2011, LIT_UNI),
    _l("Hamlet", "William Shakespeare", "Cátedra", 2012, LIT_UNI),
    _l("Orgullo y prejuicio", "Jane Austen", "Alba", 2013, LIT_UNI, popular=True),
    _l("Crimen y castigo", "Fiódor Dostoievski", "Alianza", 2015, LIT_UNI),
    _l("1984", "George Orwell", "Debolsillo", 2013, LIT_UNI, popular=True),
    _l("Un mundo feliz", "Aldous Huxley", "Debolsillo", 2014, LIT_UNI),
    _l("Frankenstein", "Mary Shelley", "Alianza", 2012, LIT_UNI),
    _l("Drácula", "Bram Stoker", "Valdemar", 2010, LIT_UNI),
    _l("Moby Dick", "Herman Melville", "Austral", 2014, LIT_UNI),
    _l("El gran Gatsby", "F. Scott Fitzgerald", "Debolsillo", 2011, LIT_UNI),
    _l("Madame Bovary", "Gustave Flaubert", "Cátedra", 2012, LIT_UNI),
    _l("Los miserables", "Victor Hugo", "Alianza", 2013, LIT_UNI),
    _l("La metamorfosis", "Franz Kafka", "Alianza", 2011, LIT_UNI, popular=True),
    _l("Cumbres borrascosas", "Emily Brontë", "Alba", 2014, LIT_UNI),
    _l("Ana Karenina", "León Tolstói", "Alba", 2010, LIT_UNI),
    _l("El retrato de Dorian Gray", "Oscar Wilde", "Austral", 2013, LIT_UNI),
    _l("Fahrenheit 451", "Ray Bradbury", "Minotauro", 2012, LIT_UNI),
    _l("La comunidad del anillo", "J. R. R. Tolkien", "Minotauro", 2012, LIT_UNI, popular=True),
    _l("El hobbit", "J. R. R. Tolkien", "Minotauro", 2012, LIT_UNI),
    _l("Matar a un ruiseñor", "Harper Lee", "HarperCollins", 2015, LIT_UNI),
    _l("El diario de Ana Frank", "Ana Frank", "Debolsillo", 2013, LIT_UNI),
    _l("Ensayo sobre la ceguera", "José Saramago", "Alfaguara", 2010, LIT_UNI),
    _l("El alquimista", "Paulo Coelho", "Planeta", 2012, LIT_UNI),
    _l("El código Da Vinci", "Dan Brown", "Planeta", 2003, LIT_UNI),
    _l("Alas de sangre", "Rebecca Yarros", "Planeta", 2023, LIT_UNI, popular=True),
    _l("Alas de hierro", "Rebecca Yarros", "Planeta", 2024, LIT_UNI, popular=True),
    _l("Alas de ónix", "Rebecca Yarros", "Planeta", 2025, LIT_UNI, popular=True),
    # --- infantil y juvenil ---
    _l("Harry Potter y la piedra filosofal", "J. K. Rowling", "Salamandra", 2015, INFANTIL, popular=True),
    _l("Harry Potter y la cámara secreta", "J. K. Rowling", "Salamandra", 2015, INFANTIL, popular=True),
    _l("Los juegos del hambre", "Suzanne Collins", "Molino", 2012, INFANTIL),
    _l("Matilda", "Roald Dahl", "Alfaguara", 2016, INFANTIL),
    _l("Charlie y la fábrica de chocolate", "Roald Dahl", "Alfaguara", 2016, INFANTIL),
    _l("Alicia en el país de las maravillas", "Lewis Carroll", "Alianza", 2010, INFANTIL),
    _l("El león, la bruja y el ropero", "C. S. Lewis", "Destino", 2005, INFANTIL),
    _l("El reino del revés", "María Elena Walsh", "Alfaguara", 2015, INFANTIL),
    _l("Socorro (12 cuentos para caerse de miedo)", "Elsa Bornemann", "Alfaguara", 2017, INFANTIL),
    _l("Cuentos de la selva", "Horacio Quiroga", "Losada", 2004, INFANTIL),
    _l("Mujercitas", "Louisa May Alcott", "Alba", 2014, INFANTIL),
    # --- ciencias sociales y desarrollo personal ---
    _l("Hábitos atómicos", "James Clear", "Paidós", 2020, SOCIALES, popular=True),
    _l("Este dolor no es mío", "Mark Wolynn", "Gaia", 2017, SOCIALES, popular=True),
    _l("Pensar rápido, pensar despacio", "Daniel Kahneman", "Debate", 2012, SOCIALES),
    _l("Padre rico, padre pobre", "Robert T. Kiyosaki", "Debolsillo", 2015, SOCIALES),
    # --- historia ---
    _l("Los mitos de la historia argentina", "Felipe Pigna", "Planeta", 2004, HISTORIA),
    _l("Breve historia de la Argentina", "José Luis Romero", "Fondo de Cultura Económica", 2013, HISTORIA),
    _l("Historia contemporánea de América Latina", "Tulio Halperín Donghi", "Alianza", 2005, HISTORIA),
    _l("Homo Deus", "Yuval Noah Harari", "Debate", 2016, HISTORIA),
    # --- ciencias naturales ---
    _l("Breve historia del tiempo", "Stephen Hawking", "Crítica", 2011, NATURALES, popular=True),
    _l("El origen de las especies", "Charles Darwin", "Austral", 2010, NATURALES),
    _l("El gen egoísta", "Richard Dawkins", "Salvat", 2014, NATURALES),
    _l("Una breve historia de casi todo", "Bill Bryson", "RBA", 2005, NATURALES),
    # --- filosofía ---
    _l("El mundo de Sofía", "Jostein Gaarder", "Siruela", 2012, FILOSOFIA),
    _l("Meditaciones", "Marco Aurelio", "Gredos", 2010, FILOSOFIA),
    _l("La República", "Platón", "Gredos", 2011, FILOSOFIA),
    _l("Así habló Zaratustra", "Friedrich Nietzsche", "Alianza", 2011, FILOSOFIA),
    _l("Los cuatro acuerdos", "Miguel Ruiz", "Urano", 2012, FILOSOFIA),
    # --- arte y música ---
    _l("La historia del arte", "E. H. Gombrich", "Phaidon", 2008, ARTE),
    _l("Modos de ver", "John Berger", "Gustavo Gili", 2016, ARTE),
    # --- tecnología e informática ---
    _l("The Pragmatic Programmer", "Andrew Hunt; David Thomas", "Addison-Wesley", 2019, TECNO, popular=True),
    _l("Refactoring", "Martin Fowler", "Addison-Wesley", 2018, TECNO),
    _l("Domain-Driven Design", "Eric Evans", "Addison-Wesley", 2003, TECNO),
    _l("Patterns of Enterprise Application Architecture", "Martin Fowler", "Addison-Wesley", 2002, TECNO),
    _l("Head First Design Patterns", "Eric Freeman; Elisabeth Robson", "O'Reilly", 2020, TECNO),
    _l("Introduction to Algorithms", "Thomas H. Cormen; Charles E. Leiserson; Ronald L. Rivest; Clifford Stein", "MIT Press", 2022, TECNO),
    _l("Redes de computadoras", "Andrew S. Tanenbaum; David J. Wetherall", "Pearson", 2012, TECNO),
    _l("Fundamentos de bases de datos", "Abraham Silberschatz; Henry F. Korth; S. Sudarshan", "McGraw-Hill", 2014, TECNO),
    _l("Python Crash Course", "Eric Matthes", "No Starch Press", 2023, TECNO),
    _l("Fluent Python", "Luciano Ramalho", "O'Reilly", 2022, TECNO),
    _l("Eloquent JavaScript", "Marijn Haverbeke", "No Starch Press", 2018, TECNO),
    _l("El mítico hombre-mes", "Frederick P. Brooks", "Addison-Wesley", 1995, TECNO),
    # --- obras de referencia ---
    _l("Diccionario panhispánico de dudas", "Real Academia Española", "Santillana", 2005, REFERENCIA, OBRA_REF),
]  # fmt: skip

NOMBRES = (
    "Agustina Alejandro Ana Andrés Antonella Bautista Belén Camila Carolina Catalina Daniel "
    "Delfina Emilia Ezequiel Facundo Federico Florencia Franco Gabriela Guadalupe Ignacio Joaquín "
    "Josefina Juan Julieta Lautaro Leandro Lucía Luciana Manuel Marcela Mariano Martina Matías "
    "Micaela Milagros Nahuel Nicolás Paula Pilar Ramiro Renata Santiago Sebastián Sol Tobías "
    "Valentín Victoria Ximena"
).split()
APELLIDOS = (
    "Aguirre Álvarez Benítez Cabrera Castro Córdoba Díaz Domínguez Fernández Figueroa Flores "
    "Giménez Godoy González Gutiérrez Herrera Ledesma López Luna Martínez Medina Molina Morales "
    "Navarro Núñez Ortiz Pereyra Pérez Ramírez Ríos Rodríguez Rojas Romero Ruiz Sánchez Silva "
    "Sosa Suárez Torres Vázquez Vega Villalba"
).split()

SEDES = ("CEN", "NORTE", "SUR_RC", "VMARIA")
BIBLIOTECARIOS = {
    "CEN": "bibliotecario.cen",
    "NORTE": "bibliotecario.norte",
    "SUR_RC": "bibliotecario.rc",
    "VMARIA": "bibliotecario.vm",
}
ABRE_SABADO = {"CEN": True, "NORTE": True, "SUR_RC": False, "VMARIA": True}
PESO_SEDE = {"CEN": 0.35, "NORTE": 0.3, "SUR_RC": 0.2, "VMARIA": 0.15}
CANTIDAD_SOCIOS = 72
REMITOS_ABIERTOS = ("GENERADO", "EMPAQUETADO", "DESPACHADO", "EN_TRANSITO")
DANIOS = (
    "Hojas manchadas con café",
    "Lomo despegado",
    "Tapa doblada por la humedad",
    "Páginas arrancadas al final",
)


def isbn_de_demostracion(n: int) -> str:
    """ISBN-13 válido y único (prefijo 978-987-9, que no usa la historia)."""
    base = f"9789879{n:05d}"
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
    return base + str((10 - suma % 10) % 10)


def codigo_volumen(sede: str, indice: int, n: int) -> str:
    return f"{sede.replace('_', '')}-V{indice:03d}-{n}"


def _sin_tildes(texto: str) -> str:
    tabla = str.maketrans("áéíóúÁÉÍÓÚñÑü", "aeiouAEIOUnNu")
    return texto.translate(tabla)


class Volumen:
    """Suma catálogo, socios y dos meses de movimiento a la historia de demostración."""

    def __init__(
        self, historia: "Historia", avisar: Callable[[str], None] = lambda _texto: None
    ) -> None:
        self.h = historia
        self.avisar = avisar
        self.d = historia.d
        self.rng = random.Random(20261115)
        self.libros: list[int] = []
        self.pesos: list[float] = []
        self.socios: dict[str, list[int]] = {s: [] for s in SEDES}
        self.devolver_el: dict[int, date | None] = {}
        self.pagar_el: dict[int, date | None] = {}
        self.no_retira: set[int] = set()
        self.renovacion_intentada: set[int] = set()
        self.transito: dict[int, int] = {}
        self._biblios: dict[str, Usuario] = {}
        self.reparar_el: dict[int, date] = {}

    # --- utilidades -----------------------------------------------------------------------

    def biblio(self, sede: str) -> Usuario:
        if sede not in self._biblios:
            self._biblios[sede] = self.h.u(BIBLIOTECARIOS[sede])
        return self._biblios[sede]

    def sede_id(self, sede: str) -> int:
        return self.h.sede_ids[sede]

    def _intentar(self, accion, *args, **kwargs):
        """Ejecuta un caso de uso; si la regla de negocio lo rechaza, sigue sin él."""
        try:
            return accion(*args, **kwargs)
        except ErrorDeNegocio:
            return None

    def _sede_al_azar(self, opciones: tuple[str, ...] = SEDES) -> str:
        return self.rng.choices(opciones, weights=[PESO_SEDE[s] for s in opciones])[0]

    # --- fundación: catálogo y socios -----------------------------------------------------

    def fundar(self) -> None:
        """Hace 84 a 61 días: el administrador carga el catálogo; las sedes, ejemplares y socios."""
        admin = self.h.u("admin")
        categorias = {c.nombre: c.id for c in self.d.catalogo.categorias(admin)}
        for i, libro in enumerate(LIBROS_VOLUMEN):
            self.h.en(84 - i // 20, 9 + (i % 20) // 3, (i * 7) % 60)
            creado = self.d.catalogo.crear_libro(
                admin,
                DatosLibroNuevo(
                    titulo=libro.titulo,
                    autores=list(libro.autores),
                    categoria_id=categorias[libro.categoria],
                    tipo_material=libro.tipo,
                    isbn=None if libro.tipo == REVISTA else isbn_de_demostracion(i + 1),
                    editorial=libro.editorial,
                    anio_edicion=libro.anio,
                    portada_url=portada_de(libro.titulo),
                ),
            )
            assert creado.id is not None
            self.libros.append(creado.id)
            self.pesos.append(6.0 if libro.popular else self.rng.uniform(0.4, 1.6))
        self._ejemplares()
        self._socios()

    def _ejemplares(self) -> None:
        """Los populares tienen de 3 a 5 ejemplares; el resto, 1 o 2 (Villa María recién abrió)."""
        por_sede: dict[str, list[tuple[int, int]]] = {s: [] for s in SEDES}
        for i, libro in enumerate(LIBROS_VOLUMEN, start=1):
            cantidad = self.rng.randint(3, 5) if libro.popular else self.rng.randint(1, 2)
            contador: dict[str, int] = {}
            for _ in range(cantidad):
                sede = self._sede_al_azar()
                contador[sede] = contador.get(sede, 0) + 1
                por_sede[sede].append((i, contador[sede]))
        for dia, sede in ((78, "CEN"), (77, "NORTE"), (76, "SUR_RC"), (62, "VMARIA")):
            biblio = self.biblio(sede)
            for j, (indice, n) in enumerate(por_sede[sede]):
                self.h.en(dia, 9 + j // 12, (j * 5) % 60)
                estado = EstadoFisico.NUEVO if self.rng.random() < 0.3 else EstadoFisico.BUENO
                self.d.catalogo.crear_ejemplar(
                    biblio,
                    DatosEjemplarNuevo(
                        libro_id=self.libros[indice - 1],
                        codigo_inventario=codigo_volumen(sede, indice, n),
                        estado_fisico=estado,
                    ),
                )

    def _socios(self) -> None:
        nombres_usados: set[tuple[str, str]] = set()
        for i in range(CANTIDAD_SOCIOS):
            sede = self._sede_al_azar()
            dias = 61 + (i % 3) if sede == "VMARIA" else 79 - (i * 16) // CANTIDAD_SOCIOS
            self.h.en(dias, 10 + i % 8, (i * 11) % 60)
            nombre, apellido = self.rng.choice(NOMBRES), self.rng.choice(APELLIDOS)
            while (nombre, apellido) in nombres_usados:
                nombre, apellido = self.rng.choice(NOMBRES), self.rng.choice(APELLIDOS)
            nombres_usados.add((nombre, apellido))
            nacimiento = date(self.rng.randint(1950, 2007), self.rng.randint(1, 12), 1) + (
                timedelta(days=self.rng.randint(0, 27))
            )
            correo = _sin_tildes(f"{nombre}.{apellido}{i}").lower() + "@example.com"
            socio = self._intentar(
                self.d.socios.crear,
                self.biblio(sede),
                DatosSocio(
                    tipo_documento=TipoDocumento.DNI,
                    nro_documento=str(41_000_000 + i * 1_337),
                    nombre=nombre,
                    apellido=apellido,
                    fecha_nacimiento=nacimiento,
                    email=correo if self.rng.random() < 0.8 else None,
                    telefono=f"+54351{self.rng.randint(4000000, 6999999)}"
                    if self.rng.random() < 0.6
                    else None,
                ),
            )
            if socio is not None and socio.id is not None:
                self.socios[sede].append(socio.id)

    # --- dos meses de movimiento ----------------------------------------------------------

    def simular(self, desde: int = 59, hasta: int = 1) -> None:
        """Recorre cada día, de hace ``desde`` días a hace ``hasta`` días."""
        for dias in range(desde, hasta - 1, -1):
            if dias % 10 == 0 or dias == desde:
                self.avisar(f"Movimiento diario: faltan {dias} días...")
            self.h.en(dias, 0, 5)
            dia = self.d.reloj.hoy()
            # Las tareas automáticas de cada madrugada.
            self.d.prestamos.detectar_vencidos()
            self.d.reservas.vencer_reservas()
            self.d.prestamos.vencer_retiros()
            if dia.isoweekday() == 7:
                continue
            abiertas = [s for s in SEDES if dia.isoweekday() < 6 or ABRE_SABADO[s]]
            self.h.en(dias, 9, 15)
            self._logistica(dia, abiertas)
            if dia.isoweekday() == 1:
                self._traslado_semanal()
            for k, sede in enumerate(abiertas):
                self.h.en(dias, 10 + k, 0)
                self._devoluciones(dia, sede)
                self.h.en(dias, 11 + k, 10)
                self._retiros_y_entregas(sede)
                self.h.en(dias, 15 + k, 20)
                self._prestamos_nuevos(dia, sede)
                self.h.en(dias, 16 + k, 30)
                self._renovaciones(dia, sede)
                self._pagos(dia, sede)
                self.h.en(dias, 17 + k, 40)
                self._reparaciones(dia, sede)
                self._cancelaciones_de_reservas(dia, sede)

    def _logistica(self, dia: date, abiertas: list[str]) -> None:
        """Cada mañana: armar los envíos pedidos, empaquetar, despachar y recibir lo que llegó."""
        sedes = {self.sede_id(s): s for s in abiertas}
        en_remito = (
            select(DetalleRemitoORM.ejemplar_id)
            .join(RemitoORM, RemitoORM.id == DetalleRemitoORM.remito_id)
            .where(RemitoORM.estado.in_(REMITOS_ABIERTOS))
        )
        pedidos = self.h.sesion.execute(
            select(PrestamoORM.id, PrestamoORM.ejemplar_id, PrestamoORM.sede_origen_id,
                   PrestamoORM.sede_destino_id)
            .where(
                PrestamoORM.tipo == "INTERBIBLIOTECARIO",
                PrestamoORM.estado == "SOLICITADO",
                PrestamoORM.ejemplar_id.not_in(en_remito),
            )
            .order_by(PrestamoORM.id)
        ).all()  # fmt: skip
        grupos: dict[tuple[int, int], list[LineaNueva]] = {}
        for pid, ejemplar_id, origen, destino in pedidos:
            if origen in sedes:
                grupos.setdefault((origen, destino), []).append(LineaNueva(ejemplar_id, pid))
        for (origen, destino), lineas in grupos.items():
            self._intentar(
                self.d.remitos.generar,
                self.biblio(sedes[origen]),
                destino,
                MotivoRemito.ENVIO,
                lineas,
                None,
            )
        abiertos = self.h.sesion.execute(
            select(RemitoORM.id, RemitoORM.estado, RemitoORM.sede_origen_id,
                   RemitoORM.sede_destino_id, RemitoORM.fecha_despacho)
            .where(RemitoORM.estado.in_(REMITOS_ABIERTOS))
            .order_by(RemitoORM.id)
        ).all()  # fmt: skip
        for rid, estado, origen, destino, despacho in abiertos:
            if estado == "GENERADO" and origen in sedes and self.rng.random() < 0.85:
                self._intentar(self.d.remitos.empaquetar, self.biblio(sedes[origen]), rid)
                estado = "EMPAQUETADO"
            if estado == "EMPAQUETADO" and origen in sedes and self.rng.random() < 0.8:
                self._intentar(self.d.remitos.despachar, self.biblio(sedes[origen]), rid)
                continue
            if estado not in ("DESPACHADO", "EN_TRANSITO") or despacho is None:
                continue
            transito = self.transito.setdefault(rid, self.rng.randint(1, 3))
            llego = (dia - despacho.astimezone(self.d.reloj.ahora_local().tzinfo).date()).days
            if llego >= transito and destino in sedes:
                self._recibir(rid, sedes[destino])
            elif estado == "DESPACHADO" and origen in sedes and self.rng.random() < 0.5:
                self._intentar(self.d.remitos.pasar_a_transito, self.biblio(sedes[origen]), rid)

    def _recibir(self, remito_id: int, sede: str) -> None:
        lineas = self.h.sesion.execute(
            select(DetalleRemitoORM.ejemplar_id, DetalleRemitoORM.estado_fisico_salida).where(
                DetalleRemitoORM.remito_id == remito_id
            )
        ).all()
        recepcion = []
        for ejemplar_id, salida in lineas:
            if self.rng.random() < 0.03:
                recepcion.append(
                    RecepcionLinea(
                        ejemplar_id, EstadoFisico.DANADO, observacion=self.rng.choice(DANIOS)
                    )
                )
            else:
                recepcion.append(RecepcionLinea(ejemplar_id, EstadoFisico(salida)))
        self._intentar(self.d.remitos.recibir, self.biblio(sede), remito_id, recepcion)

    def _traslado_semanal(self) -> None:
        """Los lunes, Central reparte a Villa María y a Río Cuarto copias que sobran."""
        destino = self.rng.choice(("VMARIA", "SUR_RC"))
        disponibles = self.h.sesion.scalars(
            select(EjemplarORM.id)
            .where(
                EjemplarORM.sede_propietaria_id == self.sede_id("CEN"),
                EjemplarORM.sede_actual_id == self.sede_id("CEN"),
                EjemplarORM.estado == "DISPONIBLE",
                EjemplarORM.codigo_inventario.like("CEN-V%"),
            )
            .order_by(EjemplarORM.id)
        ).all()
        if len(disponibles) < 6:
            return
        elegidos = self.rng.sample(disponibles, 2)
        self._intentar(
            self.d.remitos.generar,
            self.biblio("CEN"),
            self.sede_id(destino),
            MotivoRemito.TRASLADO,
            [LineaNueva(e, None) for e in elegidos],
            "Redistribución semanal de la colección",
        )

    def _devoluciones(self, dia: date, sede: str) -> None:
        en_manos = self.h.sesion.execute(
            select(PrestamoORM.id, PrestamoORM.fecha_vencimiento)
            .where(
                PrestamoORM.estado.in_(("ACTIVO", "VENCIDO")),
                PrestamoORM.sede_destino_id == self.sede_id(sede),
                PrestamoORM.socio_id.in_(self._todos_los_socios()),
            )
            .order_by(PrestamoORM.id)
        ).all()
        for pid, vence in en_manos:
            if pid not in self.devolver_el:
                self.devolver_el[pid] = self._plan_de_devolucion(vence)
            plan = self.devolver_el[pid]
            if plan is None or plan > dia:
                continue
            azar = self.rng.random()
            if azar < 0.8:
                estado, obs = EstadoRecibido.BUENO, None
            elif azar < 0.93:
                estado, obs = EstadoRecibido.REGULAR, "Algunas hojas subrayadas"
            elif azar < 0.985:
                estado, obs = EstadoRecibido.DANADO, self.rng.choice(DANIOS)
            else:
                estado, obs = EstadoRecibido.EXTRAVIADO, "El socio informó que lo perdió"
            self._intentar(self.d.devoluciones.registrar, self.biblio(sede), pid, estado, obs)

    def _plan_de_devolucion(self, vence: date) -> date | None:
        """La mayoría devuelve en término; algunos tarde y unos pocos no devuelven."""
        azar = self.rng.random()
        if azar < 0.025:
            return None
        if azar < 0.15:
            return vence + timedelta(days=self.rng.randint(1, 9))
        return vence - timedelta(days=self.rng.randint(0, 9))

    def _retiros_y_entregas(self, sede: str) -> None:
        """Reservas listas que el socio retira y envíos que llegaron y el socio pasa a buscar."""
        biblio, sede_id = self.biblio(sede), self.sede_id(sede)
        listas = self.h.sesion.scalars(
            select(ReservaORM.id).where(
                ReservaORM.estado == "DISPONIBLE_PARA_RETIRO", ReservaORM.sede_retiro_id == sede_id
            )
        ).all()
        for rid in listas:
            if self.rng.random() < 0.6:
                self._intentar(self.d.reservas.retirar, biblio, rid)
        llegados = self.h.sesion.scalars(
            select(PrestamoORM.id)
            .join(EjemplarORM, EjemplarORM.id == PrestamoORM.ejemplar_id)
            .where(
                PrestamoORM.estado == "EN_ENVIO",
                PrestamoORM.sede_destino_id == sede_id,
                EjemplarORM.estado == "APARTADO",
                EjemplarORM.sede_actual_id == sede_id,
            )
        ).all()
        for pid in llegados:
            if pid in self.no_retira:
                continue
            if self.rng.random() < 0.04:
                self.no_retira.add(pid)  # no lo retira: vence el plazo y vuelve a su sede
            elif self.rng.random() < 0.75:
                self._intentar(self.d.prestamos.entregar, biblio, pid)

    def _prestamos_nuevos(self, dia: date, sede: str) -> None:
        biblio, sede_id = self.biblio(sede), self.sede_id(sede)
        cantidad = self.rng.randint(2, 5) if dia.isoweekday() < 6 else self.rng.randint(0, 2)
        elegibles = self._socios_que_pueden_pedir()
        if not elegibles:
            return
        propios = [s for s in self.socios[sede] if s in elegibles]
        for _ in range(cantidad):
            if propios and self.rng.random() < 0.85:
                socio = self.rng.choice(propios)
            else:
                socio = self.rng.choice(sorted(elegibles))
            libro = self.rng.choices(self.libros, weights=self.pesos)[0]
            local = self._disponible(libro, [sede_id])
            if local is not None:
                prestamo = self._intentar(self.d.prestamos.registrar, biblio, socio, local)
                if prestamo is not None and prestamo.id is not None:
                    self._intentar(self.d.prestamos.entregar, biblio, prestamo.id)
                continue
            otras = [self.sede_id(s) for s in SEDES if s != sede]
            lejano = self._disponible(libro, otras)
            if lejano is not None and self.rng.random() < 0.75:
                self._intentar(self.d.prestamos.registrar, biblio, socio, lejano)
            elif lejano is None and self.rng.random() < 0.35:
                self._intentar(self.d.reservas.reservar, biblio, libro, sede_id, socio)

    def _socios_que_pueden_pedir(self) -> set[int]:
        """Habilitados y con menos de tres préstamos en curso (el resto lo valida el caso de uso)."""
        abiertos = (
            select(PrestamoORM.socio_id)
            .where(PrestamoORM.estado.in_(("SOLICITADO", "EN_ENVIO", "ACTIVO", "VENCIDO")))
            .group_by(PrestamoORM.socio_id)
            .having(func.count(PrestamoORM.id) >= 3)
        )
        return set(
            self.h.sesion.scalars(
                select(SocioORM.id).where(
                    SocioORM.id.in_(self._todos_los_socios()),
                    SocioORM.estado == "HABILITADO",
                    SocioORM.id.not_in(abiertos),
                )
            )
        )

    def _disponible(self, libro_id: int, sedes: list[int]) -> int | None:
        return self.h.sesion.scalar(
            select(EjemplarORM.id)
            .where(
                EjemplarORM.libro_id == libro_id,
                EjemplarORM.estado == "DISPONIBLE",
                EjemplarORM.sede_actual_id.in_(sedes),
                EjemplarORM.sede_propietaria_id == EjemplarORM.sede_actual_id,
            )
            .order_by(EjemplarORM.id)
            .limit(1)
        )

    def _renovaciones(self, dia: date, sede: str) -> None:
        por_vencer = self.h.sesion.execute(
            select(PrestamoORM.id, PrestamoORM.fecha_vencimiento).where(
                PrestamoORM.estado == "ACTIVO",
                PrestamoORM.sede_destino_id == self.sede_id(sede),
                PrestamoORM.socio_id.in_(self._todos_los_socios()),
            )
        ).all()
        for pid, vence in por_vencer:
            if pid in self.renovacion_intentada or vence is None or (vence - dia).days > 2:
                continue
            self.renovacion_intentada.add(pid)
            if self.rng.random() < 0.25:
                renovado = self._intentar(self.d.prestamos.renovar, self.biblio(sede), pid)
                if renovado is not None:
                    self.devolver_el.pop(pid, None)  # con el plazo nuevo, vuelve a planear

    def _pagos(self, dia: date, sede: str) -> None:
        pendientes = self.h.sesion.execute(
            select(MultaORM.id, MultaORM.fecha_generacion)
            .join(PrestamoORM, PrestamoORM.id == MultaORM.prestamo_id)
            .where(
                MultaORM.estado == "PENDIENTE",
                PrestamoORM.sede_destino_id == self.sede_id(sede),
                PrestamoORM.socio_id.in_(self._todos_los_socios()),
            )
        ).all()
        zona = self.d.reloj.ahora_local().tzinfo
        for mid, generada in pendientes:
            if mid not in self.pagar_el:
                demora = self.rng.randint(0, 6)
                self.pagar_el[mid] = (
                    None
                    if self.rng.random() < 0.08
                    else generada.astimezone(zona).date() + timedelta(days=demora)
                )
            plan = self.pagar_el[mid]
            if plan is None or plan > dia:
                continue
            medio = self.rng.choice(
                (MedioPago.EFECTIVO, MedioPago.DEBITO, MedioPago.CREDITO, MedioPago.TRANSFERENCIA)
            )
            comprobante = (
                None if medio == MedioPago.EFECTIVO else f"Op. {self.rng.randint(10**7, 10**8 - 1)}"
            )
            self._intentar(
                self.d.pagos.saldar_en_mostrador, self.biblio(sede), mid, medio, comprobante
            )

    def _reparaciones(self, dia: date, sede: str) -> None:
        """Los ejemplares dañados de la sede vuelven a circular después de unos días de taller."""
        sede_id = self.sede_id(sede)
        en_revision = self.h.sesion.execute(
            select(EjemplarORM.id, EjemplarORM.version).where(
                EjemplarORM.estado == "EN_REVISION",
                EjemplarORM.sede_propietaria_id == sede_id,
                EjemplarORM.sede_actual_id == sede_id,
                EjemplarORM.codigo_inventario.like("%-V%"),
            )
        ).all()
        for ejemplar_id, version in en_revision:
            listo = self.reparar_el.setdefault(
                ejemplar_id, dia + timedelta(days=self.rng.randint(2, 6))
            )
            if listo <= dia:
                self._intentar(
                    self.d.catalogo.reparar_ejemplar, self.biblio(sede), ejemplar_id, version
                )

    def _cancelaciones_de_reservas(self, dia: date, sede: str) -> None:
        """De vez en cuando un socio que esperaba hace rato ya no necesita el libro."""
        if self.rng.random() > 0.12:
            return
        limite = self.d.reloj.ahora() - timedelta(days=7)
        viejas = self.h.sesion.scalars(
            select(ReservaORM.id)
            .where(
                ReservaORM.estado == "PENDIENTE",
                ReservaORM.sede_retiro_id == self.sede_id(sede),
                ReservaORM.socio_id.in_(self._todos_los_socios()),
                ReservaORM.fecha_reserva < limite,
            )
            .order_by(ReservaORM.id)
        ).all()
        if viejas:
            self._intentar(
                self.d.reservas.cancelar,
                self.biblio(sede),
                self.rng.choice(viejas),
                "El socio avisó que ya no lo necesita",
            )

    def _todos_los_socios(self) -> list[int]:
        return [s for socios in self.socios.values() for s in socios]
