from datetime import datetime

from pydantic import BaseModel, Field


class ConfiguracaoResponse(BaseModel):
    nome_empresa  : str
    atualizado_em : datetime | None

    model_config = {"from_attributes": True}


class ConfiguracaoUpdate(BaseModel):
    nome_empresa: str = Field(..., min_length=1, max_length=200)
