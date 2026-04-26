from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EntrevistaCreate(BaseModel):
    candidatura_id : UUID
    tipo           : str   # "rh" | "tecnica"
    agendada_para  : datetime

class EntrevistaResultado(BaseModel):
    score_manual  : float        # 0–10
    anotacoes     : str
    pontos_fortes : list[str] = []
    pontos_fracos : list[str] = []

class EntrevistaResponse(BaseModel):
    id               : UUID
    candidatura_id   : UUID
    entrevistador_id : UUID
    tipo             : str
    status           : str
    score_manual     : float | None
    anotacoes        : str | None
    pontos_fortes    : list[str] | None
    pontos_fracos    : list[str] | None
    agendada_para    : datetime | None
    realizada_em     : datetime | None
    criado_em        : datetime

    model_config = {"from_attributes": True}