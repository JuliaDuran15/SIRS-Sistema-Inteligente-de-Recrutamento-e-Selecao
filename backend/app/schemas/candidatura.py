from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.candidatura import StatusCandidatura

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

    model_config = {"from_attributes": True}