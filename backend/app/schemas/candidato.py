from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


def _strip(v: str | None) -> str | None:
    return v.strip() if isinstance(v, str) else v


class FormacaoItem(BaseModel):
    curso        : str = Field(..., min_length=1, max_length=200)
    instituicao  : str = Field(..., min_length=1, max_length=200)
    nivel        : str = Field(..., max_length=50)
    # "tecnico" | "graduacao" | "especializacao" | "mba" | "mestrado" | "doutorado"
    status       : str = Field(..., max_length=50)
    # "concluido" | "em_andamento" | "trancado"
    ano_conclusao: int | None = Field(None, ge=1900, le=2100)

    @field_validator("curso", "instituicao", "nivel", "status", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)


class CandidatoCreate(BaseModel):
    nome            : str            = Field(..., min_length=1, max_length=200)
    email           : EmailStr
    telefone        : str | None     = Field(None, max_length=30)
    data_nascimento : date | None    = None
    logradouro      : str | None     = Field(None, max_length=200)
    numero          : str | None     = Field(None, max_length=20)
    complemento     : str | None     = Field(None, max_length=100)
    bairro          : str | None     = Field(None, max_length=100)
    cidade          : str | None     = Field(None, max_length=100)
    estado          : str | None     = Field(None, max_length=2)
    cep             : str | None     = Field(None, max_length=10)
    formacao        : list[FormacaoItem] = []

    @field_validator("nome", "telefone", "logradouro", "numero", "complemento",
                     "bairro", "cidade", "estado", "cep", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)


class CandidatoResponse(BaseModel):
    id              : UUID
    nome            : str
    email           : str
    telefone        : str | None
    data_nascimento : date | None
    logradouro      : str | None
    numero          : str | None
    complemento     : str | None
    bairro          : str | None
    cidade          : str | None
    estado          : str | None
    cep             : str | None
    formacao        : Any
    tem_candidatura_externa : bool = False
    criado_em       : datetime

    model_config = {"from_attributes": True}

class CandidatoListResponse(BaseModel):
    """Resposta paginada para GET /candidatos/."""
    items  : list[CandidatoResponse]
    total  : int
    limit  : int
    offset : int


class AlterarEmailRequest(BaseModel):
    email_novo: EmailStr


class CandidatoUpdate(BaseModel):
    nome            : str | None     = Field(None, min_length=1, max_length=200)
    telefone        : str | None     = Field(None, max_length=30)
    data_nascimento : date | None    = None
    logradouro      : str | None     = Field(None, max_length=200)
    numero          : str | None     = Field(None, max_length=20)
    complemento     : str | None     = Field(None, max_length=100)
    bairro          : str | None     = Field(None, max_length=100)
    cidade          : str | None     = Field(None, max_length=100)
    estado          : str | None     = Field(None, max_length=2)
    cep             : str | None     = Field(None, max_length=10)
    formacao        : list[FormacaoItem] | None = None

    @field_validator("nome", "telefone", "logradouro", "numero", "complemento",
                     "bairro", "cidade", "estado", "cep", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)
