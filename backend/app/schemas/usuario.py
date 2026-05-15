from datetime import datetime
from uuid import UUID

from app.models.usuario import PapelUsuario
from pydantic import BaseModel, EmailStr, Field, field_validator


class UsuarioUpdate(BaseModel):
    nome  : str | None          = Field(None, min_length=2, max_length=150)
    email : EmailStr | None     = None
    papel : PapelUsuario | None = None
    senha : str | None          = Field(None, min_length=8, max_length=128)

    @field_validator("nome", mode="before")
    @classmethod
    def strip_nome(cls, v):
        return v.strip() if isinstance(v, str) else v


class UsuarioCreate(BaseModel):
    nome  : str          = Field(..., min_length=2, max_length=150)
    email : EmailStr
    senha : str          = Field(..., min_length=8, max_length=128)
    papel : PapelUsuario = PapelUsuario.RH

    @field_validator("nome", mode="before")
    @classmethod
    def strip_nome(cls, v):
        return v.strip() if isinstance(v, str) else v

class UsuarioResponse(BaseModel):
    id        : UUID
    nome      : str
    email     : str
    papel     : PapelUsuario
    ativo     : bool
    criado_em : datetime

    model_config = {"from_attributes": True}
