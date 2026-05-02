from datetime import datetime
from uuid import UUID

from app.models.usuario import PapelUsuario
from pydantic import BaseModel, EmailStr


class UsuarioUpdate(BaseModel):
    nome  : str | None = None
    email : EmailStr | None = None
    papel : PapelUsuario | None = None
    senha : str | None = None   # se informada, substitui a senha atual


class UsuarioCreate(BaseModel):
    nome  : str
    email : EmailStr
    senha : str
    papel : PapelUsuario = PapelUsuario.RH

class UsuarioResponse(BaseModel):
    id        : UUID
    nome      : str
    email     : str
    papel     : PapelUsuario
    ativo     : bool
    criado_em : datetime

    model_config = {"from_attributes": True}