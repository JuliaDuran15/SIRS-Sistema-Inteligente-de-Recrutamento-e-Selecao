from uuid import UUID
from datetime import datetime
from app.models.usuario import PapelUsuario
from pydantic import BaseModel, EmailStr

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