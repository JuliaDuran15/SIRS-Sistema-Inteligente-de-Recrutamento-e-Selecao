from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.candidatura import StatusCandidatura


class CurriculoInfo(BaseModel):
    score_rh       : float | None
    score_mercado  : float | None
    score_curriculo: float | None
    processado_em  : datetime | None

    model_config = {"from_attributes": True}


class CandidatoMin(BaseModel):
    id       : UUID
    nome     : str
    email    : str
    telefone : str | None
    cidade   : str | None
    estado   : str | None
    formacao : Any

    model_config = {"from_attributes": True}


class VagaMin(BaseModel):
    id  : UUID
    nome: str

    model_config = {"from_attributes": True}


class CandidaturaCreate(BaseModel):
    candidato_id : UUID
    vaga_id      : UUID


class CandidaturaResponse(BaseModel):
    id           : UUID
    candidato_id : UUID
    vaga_id      : UUID
    status       : StatusCandidatura
    score_total  : float | None
    historico    : list | None
    criado_em    : datetime
    atualizado_em: datetime

    candidato    : CandidatoMin | None
    vaga         : VagaMin | None
    curriculo    : CurriculoInfo | None

    model_config = {"from_attributes": True}
