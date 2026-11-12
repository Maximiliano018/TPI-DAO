from pydantic import BaseModel, ConfigDict

from app.models.usuario import Usuario


class SedeResumenResponse(BaseModel):
    id: int
    codigo: str
    nombre: str


class UsuarioSesionResponse(BaseModel):
    """Usuario autenticado, con su sede y permisos (para que el frontend decida qué mostrar)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 4,
                "nombre": "María López",
                "rol": "BIBLIOTECARIO",
                "sede_id": 2,
                "sede": {"id": 2, "codigo": "NORTE", "nombre": "Sede Norte"},
                "permisos": ["SEDE_LEER_BASICO", "SEDE_LEER_PUBLICO"],
            }
        }
    )

    id: int
    nombre: str
    rol: str
    sede_id: int | None
    sede: SedeResumenResponse | None
    socio_id: int | None = None
    permisos: list[str]

    @classmethod
    def desde(cls, usuario: Usuario) -> "UsuarioSesionResponse":
        assert usuario.id is not None
        sede = (
            SedeResumenResponse(
                id=usuario.sede.id, codigo=usuario.sede.codigo, nombre=usuario.sede.nombre
            )
            if usuario.sede
            else None
        )
        return cls(
            id=usuario.id,
            nombre=usuario.nombre,
            rol=usuario.rol.value,
            sede_id=usuario.sede_id,
            sede=sede,
            socio_id=usuario.socio_id,
            permisos=sorted(p.value for p in usuario.permisos),
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioSesionResponse
