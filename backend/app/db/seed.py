"""Datos de demostración: sedes, usuarios de cada rol y socios.

Uso: ``python -m app.db.seed``. Es idempotente (se puede ejecutar varias veces) y solo corre
con ``ENTORNO=desarrollo`` o ``ENTORNO=test``, para no cargar usuarios con contraseñas
conocidas en un entorno real.

Las provincias y localidades vienen de la migración ``0003``.
"""

import sys
from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.config.security import hashear_clave
from app.db.models import (
    HistorialSedeORM,
    HorarioSedeORM,
    LocalidadORM,
    SedeORM,
    SocioORM,
    UsuarioORM,
)
from app.db.models.socio import SECUENCIA_NUMERO_SOCIO
from app.db.session import crear_fabrica_sesiones
from app.models.socio import formatear_numero_socio
from app.utils.texto import normalizar, normalizar_calle, normalizar_numero

ENTORNOS_PERMITIDOS = {"desarrollo", "test"}

SEDES = [
    {
        "codigo": "CEN",
        "nombre": "Sede Central",
        "calle": "Av. Colón",
        "numero": "1250",
        "localidad": "Córdoba",
        "telefono": "+543514221234",
        "email": "central@red.example",
        "responsable": "Laura Pérez",
        "baja": None,
    },
    {
        "codigo": "NORTE",
        "nombre": "Sede Norte",
        "calle": "Av. Rafael Núñez",
        "numero": "4500",
        "localidad": "Córdoba",
        "telefono": "+543514000000",
        "email": "norte@red.example",
        "responsable": "Ana Gómez",
        "baja": None,
    },
    {
        "codigo": "SUR_RC",
        "nombre": "Sede Río Cuarto",
        "calle": "Sobremonte",
        "numero": "120",
        "localidad": "Río Cuarto",
        "telefono": "+543584670000",
        "email": "riocuarto@red.example",
        "responsable": "Martín Díaz",
        "baja": None,
    },
    {
        "codigo": "OESTE_VCP",
        "nombre": "Sede Villa Carlos Paz",
        "calle": "Av. San Martín",
        "numero": "800",
        "localidad": "Villa Carlos Paz",
        "telefono": "+543541420000",
        "email": "vcp@red.example",
        "responsable": "Sofía Ramos",
        "baja": "Cierre por obras de ampliación",
    },
]

USUARIOS = [
    {"username": "admin", "nombre": "Administrador", "rol": "ADMIN", "sede": None},
    {
        "username": "bibliotecario.cen",
        "nombre": "Lucía Gómez",
        "rol": "BIBLIOTECARIO",
        "sede": "CEN",
    },
    {
        "username": "bibliotecario.norte",
        "nombre": "Marcos Ruiz",
        "rol": "BIBLIOTECARIO",
        "sede": "NORTE",
    },
]


def _franjas_tipicas() -> list[tuple[int, time, time]]:
    """Lunes a viernes de 9 a 13 y de 15 a 19; sábado de 9 a 13."""
    franjas = []
    for dia in range(1, 6):
        franjas.append((dia, time(9), time(13)))
        franjas.append((dia, time(15), time(19)))
    franjas.append((6, time(9), time(13)))
    return franjas


def _crear_usuario(sesion: Session, datos: dict, clave: str, admin_id: int | None) -> UsuarioORM:
    existente = sesion.scalar(select(UsuarioORM).where(UsuarioORM.username == datos["username"]))
    if existente:
        return existente
    sede_id = None
    if datos["sede"]:
        sede_id = sesion.scalar(select(SedeORM.id).where(SedeORM.codigo == datos["sede"]))
    usuario = UsuarioORM(
        username=datos["username"],
        password_hash=hashear_clave(clave),
        nombre=datos["nombre"],
        rol=datos["rol"],
        sede_id=sede_id,
        activo=True,
        creado_por_id=admin_id,
        actualizado_por_id=admin_id,
    )
    sesion.add(usuario)
    sesion.flush()
    return usuario


def _crear_sede(sesion: Session, datos: dict, admin: UsuarioORM) -> SedeORM:
    existente = sesion.scalar(select(SedeORM).where(SedeORM.codigo == datos["codigo"]))
    if existente:
        return existente
    localidad = sesion.scalar(select(LocalidadORM).where(LocalidadORM.nombre == datos["localidad"]))
    ahora = datetime.now(UTC)
    en_baja = datos["baja"] is not None
    sede = SedeORM(
        codigo=datos["codigo"],
        nombre=datos["nombre"],
        nombre_normalizado=normalizar(datos["nombre"]),
        calle=datos["calle"],
        numero=datos["numero"],
        localidad_id=localidad.id,
        direccion_normalizada=(
            f"{localidad.id}|{normalizar_calle(datos['calle'])}|{normalizar_numero(datos['numero'])}"
        ),
        telefono=datos["telefono"],
        email=datos["email"],
        responsable=datos["responsable"],
        estado="BAJA" if en_baja else "ACTIVA",
        fecha_baja=ahora if en_baja else None,
        motivo_baja=datos["baja"],
        baja_por_id=admin.id if en_baja else None,
        version=2 if en_baja else 1,
        creado_por_id=admin.id,
        actualizado_por_id=admin.id,
    )
    sesion.add(sede)
    sesion.flush()
    for dia, apertura, cierre in _franjas_tipicas():
        sesion.add(
            HorarioSedeORM(
                sede_id=sede.id, dia_semana=dia, hora_apertura=apertura, hora_cierre=cierre
            )
        )
    sesion.add(
        HistorialSedeORM(
            sede_id=sede.id,
            tipo_evento="ALTA",
            usuario_id=admin.id,
            estado_nuevo="ACTIVA",
            cambios=[],
            version_resultante=1,
        )
    )
    if en_baja:
        sesion.add(
            HistorialSedeORM(
                sede_id=sede.id,
                tipo_evento="BAJA",
                usuario_id=admin.id,
                estado_anterior="ACTIVA",
                estado_nuevo="BAJA",
                motivo=datos["baja"],
                cambios=[],
                version_resultante=2,
            )
        )
    return sede


SOCIOS = [
    {
        "documento": "30111222",
        "nombre": "Carla",
        "apellido": "Soto",
        "email": "carla.soto@example.com",
        "telefono": "+543515551111",
        "sede": "CEN",
        "usuario": "socio.demo",
    },
    {
        "documento": "28555666",
        "nombre": "Martín",
        "apellido": "Ríos",
        "email": "martin.rios@example.com",
        "telefono": None,
        "sede": "NORTE",
    },
    {
        "documento": "35222333",
        "nombre": "Sofía",
        "apellido": "Herrera",
        "email": None,
        "telefono": "+543584442222",
        "sede": "SUR_RC",
        "inhabilitado": "Daño reiterado de material prestado",
    },
    {
        "documento": "27444555",
        "nombre": "Diego",
        "apellido": "Luna",
        "email": "diego.luna@example.com",
        "telefono": None,
        "sede": "CEN",
        "baja": "Se mudó fuera de la provincia",
    },
]


def _crear_socio(sesion: Session, datos: dict, clave: str, admin: UsuarioORM) -> None:
    """Crea el socio (con número de la secuencia) y, si corresponde, su cuenta de acceso."""
    socio = sesion.scalar(
        select(SocioORM).where(
            SocioORM.tipo_documento == "DNI", SocioORM.nro_documento == datos["documento"]
        )
    )
    if socio is None:
        numero = sesion.scalar(SECUENCIA_NUMERO_SOCIO.next_value())
        inhabilitado = datos.get("inhabilitado")
        baja = datos.get("baja")
        estado = "BAJA" if baja else "INHABILITADO" if inhabilitado else "HABILITADO"
        socio = SocioORM(
            numero_socio=formatear_numero_socio(int(numero)),
            tipo_documento="DNI",
            nro_documento=datos["documento"],
            nombre=datos["nombre"],
            apellido=datos["apellido"],
            email=datos["email"],
            telefono=datos["telefono"],
            sede_alta_id=sesion.scalar(select(SedeORM.id).where(SedeORM.codigo == datos["sede"])),
            estado=estado,
            motivo_inhabilitacion="ADMINISTRATIVA" if inhabilitado else None,
            inhabilitacion_administrativa=bool(inhabilitado),
            motivo_administrativo=inhabilitado,
            fecha_baja=datetime.now(UTC) if baja else None,
            motivo_baja=baja,
            creado_por_id=admin.id,
            actualizado_por_id=admin.id,
        )
        sesion.add(socio)
        sesion.flush()
    username = datos.get("usuario")
    if username and not sesion.scalar(select(UsuarioORM).where(UsuarioORM.username == username)):
        sesion.add(
            UsuarioORM(
                username=username,
                password_hash=hashear_clave(clave),
                nombre=f"{datos['nombre']} {datos['apellido']}",
                rol="SOCIO",
                socio_id=socio.id,
                activo=True,
                creado_por_id=admin.id,
                actualizado_por_id=admin.id,
            )
        )


def cargar(sesion: Session, clave: str) -> None:
    """Carga los datos de demostración que falten (idempotente)."""
    admin = _crear_usuario(sesion, USUARIOS[0], clave, None)
    for datos in SEDES:
        _crear_sede(sesion, datos, admin)
    for datos in USUARIOS[1:]:
        _crear_usuario(sesion, datos, clave, admin.id)
    for datos in SOCIOS:
        _crear_socio(sesion, datos, clave, admin)


def main() -> int:
    settings = get_settings()
    if settings.entorno not in ENTORNOS_PERMITIDOS:
        print(f"El seed no corre con ENTORNO={settings.entorno!r}.", file=sys.stderr)
        return 1
    if not settings.seed_password:
        print("Defina SEED_PASSWORD en el entorno o en .env.", file=sys.stderr)
        return 1
    with crear_fabrica_sesiones()() as sesion:
        cargar(sesion, settings.seed_password)
        sesion.commit()
    print("Datos de demostración cargados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
