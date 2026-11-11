from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "mlopez", "password": "••••••••"}}
    )

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)
