from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EntrevistaCreate(BaseModel):
    candidatura_id : UUID
    tipo           : str
    agendada_para  : datetime


class EntrevistaResultado(BaseModel):
    score_manual  : float              = Field(...)
    anotacoes     : str                = Field(..., max_length=5000)
    pontos_fortes : list[str]          = []
    pontos_fracos : list[str]          = []

    @field_validator("pontos_fortes", "pontos_fracos", mode="before")
    @classmethod
    def limitar_itens(cls, v):
        if isinstance(v, list):
            return [str(item)[:300] for item in v[:20]]
        return v


class AnotacoesUpdate(BaseModel):
    anotacoes: str = Field(..., max_length=5000)


class EntrevistaResponse(BaseModel):
    id                : UUID
    candidatura_id    : UUID
    entrevistador_id  : UUID
    tipo              : str
    status            : str
    score_manual      : float | None
    anotacoes         : str | None
    historico_edicoes : list | None
    pontos_fortes     : list[str] | None
    pontos_fracos     : list[str] | None
    agendada_para     : datetime | None
    realizada_em      : datetime | None
    criado_em         : datetime

    model_config = {"from_attributes": True}
