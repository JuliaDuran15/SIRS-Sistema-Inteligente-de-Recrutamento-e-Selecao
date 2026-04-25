from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime, date
from typing import Any

class FormacaoItem(BaseModel):
    curso        : str
    instituicao  : str
    nivel        : str
    # "tecnico" | "graduacao" | "especializacao" | "mba" | "mestrado" | "doutorado"
    status       : str
    # "concluido" | "em_andamento" | "trancado"
    ano_conclusao: int | None = None

class CandidatoCreate(BaseModel):
    nome            : str
    email           : EmailStr
    telefone        : str | None = None
    origem          : str = "manual"
    fonte           : str | None = None
    data_nascimento : date | None = None
    logradouro      : str | None = None
    numero          : str | None = None
    complemento     : str | None = None
    bairro          : str | None = None
    cidade          : str | None = None
    estado          : str | None = None
    cep             : str | None = None
    formacao        : list[FormacaoItem] = []

class CandidatoResponse(BaseModel):
    id              : UUID
    nome            : str
    email           : str
    telefone        : str | None
    origem          : str
    fonte           : str | None
    data_nascimento : date | None
    logradouro      : str | None
    numero          : str | None
    complemento     : str | None
    bairro          : str | None
    cidade          : str | None
    estado          : str | None
    cep             : str | None
    formacao        : Any
    criado_em       : datetime

    model_config = {"from_attributes": True}

class CandidatoUpdate(BaseModel):
    nome            : str | None = None
    telefone        : str | None = None
    data_nascimento : date | None = None
    logradouro      : str | None = None
    numero          : str | None = None
    complemento     : str | None = None
    bairro          : str | None = None
    cidade          : str | None = None
    estado          : str | None = None
    cep             : str | None = None
    formacao        : list[FormacaoItem] | None = None