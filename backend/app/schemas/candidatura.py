from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.candidatura import StatusCandidatura
from pydantic import BaseModel


class CurriculoInfo(BaseModel):
    texto_extraido : str | None
    arquivo_pdf    : str | None
    score_rh       : float | None
    score_mercado  : float | None
    score_curriculo: float | None
    explicacao     : Any | None
    processado_em  : datetime | None

    model_config = {"from_attributes": True}


class CurriculoDetalhado(BaseModel):
    id              : UUID
    candidatura_id  : UUID
    texto_extraido  : str | None
    arquivo_pdf     : str | None
    score_rh        : float | None
    score_mercado   : float | None
    score_curriculo : float | None
    explicacao      : Any | None
    processado_em   : datetime | None

    model_config = {"from_attributes": True}


class CandidatoMin(BaseModel):
    id            : UUID
    nome          : str
    email         : str
    telefone      : str | None
    cidade        : str | None
    estado        : str | None
    formacao      : Any
    linkedin_url  : str | None = None
    portfolio_url : str | None = None

    model_config = {"from_attributes": True}


class VagaMin(BaseModel):
    id               : UUID
    nome             : str
    gestores_ids     : Any
    criado_por_id    : UUID | None
    rhs_autorizados  : Any

    model_config = {"from_attributes": True}


class CandidaturaRerankItem(BaseModel):
    """Item retornado pelo endpoint de reranking — adiciona score_rerank ao response padrão."""
    id              : UUID
    candidato_id    : UUID
    vaga_id         : UUID
    status          : StatusCandidatura
    score_total     : float | None
    score_curriculo : float | None      # score bi-encoder
    score_rerank    : float | None      # score cross-encoder (0–1)
    candidato       : CandidatoMin | None
    curriculo       : CurriculoInfo | None

    model_config = {"from_attributes": True}


class CandidaturaCreate(BaseModel):
    candidato_id : UUID
    vaga_id      : UUID


class CandidaturaResponse(BaseModel):
    id                   : UUID
    candidato_id         : UUID
    vaga_id              : UUID
    status               : StatusCandidatura
    score_total          : float | None
    score_entrevista_rh  : float | None
    score_entrevista_tec : float | None
    historico            : list | None
    origem               : str
    fonte                : str | None
    criado_em            : datetime
    atualizado_em        : datetime

    candidato    : CandidatoMin | None
    vaga         : VagaMin | None
    curriculo    : CurriculoInfo | None

    model_config = {"from_attributes": True}
