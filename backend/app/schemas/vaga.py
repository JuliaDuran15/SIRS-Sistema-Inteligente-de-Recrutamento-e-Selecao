from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class VagaCreate(BaseModel):
    nome             : str   = Field(..., min_length=1, max_length=200)
    requisitos_texto : str   = Field(..., min_length=1, max_length=20_000)
    gestores_ids     : list[str] = []

    # Pesos do score curricular — devem somar 1.0
    peso_rh      : float = Field(0.6,  ge=0.0, le=1.0)
    peso_mercado : float = Field(0.4,  ge=0.0, le=1.0)

    # Pesos do score consolidado final — devem somar 1.0
    peso_curriculo      : float = Field(0.50, ge=0.0, le=1.0)
    peso_entrevista_rh  : float = Field(0.25, ge=0.0, le=1.0)
    peso_entrevista_tec : float = Field(0.25, ge=0.0, le=1.0)

    @field_validator("nome", "requisitos_texto", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validar_pesos(self):
        soma_curriculo = round(self.peso_rh + self.peso_mercado, 10)
        if soma_curriculo != 1.0:
            raise ValueError(
                f"peso_rh + peso_mercado deve ser 1.0 (atual: {soma_curriculo})"
            )

        soma_final = round(
            self.peso_curriculo + self.peso_entrevista_rh + self.peso_entrevista_tec,
            10
        )
        if soma_final != 1.0:
            raise ValueError(
                f"peso_curriculo + peso_entrevista_rh + peso_entrevista_tec "
                f"deve ser 1.0 (atual: {soma_final})"
            )
        return self


class VagaResponse(BaseModel):
    id               : UUID
    nome             : str
    requisitos_texto : str
    peso_rh          : float
    peso_mercado     : float
    peso_curriculo   : float
    peso_entrevista_rh  : float
    peso_entrevista_tec : float
    status           : str
    ranking_mercado  : Any
    gestores_ids     : Any
    criado_por_id    : UUID | None
    rhs_autorizados  : Any
    criado_em        : datetime

    model_config = {"from_attributes": True}


class RhsAutorizadosUpdate(BaseModel):
    rhs_autorizados: list[str]


class VagaUpdatePesos(BaseModel):
    peso_rh             : float = Field(..., ge=0.0, le=1.0)
    peso_mercado        : float = Field(..., ge=0.0, le=1.0)
    peso_curriculo      : float = Field(..., ge=0.0, le=1.0)
    peso_entrevista_rh  : float = Field(..., ge=0.0, le=1.0)
    peso_entrevista_tec : float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validar_pesos(self):
        soma_curriculo = round(self.peso_rh + self.peso_mercado, 10)
        if soma_curriculo != 1.0:
            raise ValueError(
                f"peso_rh + peso_mercado deve ser 1.0 (atual: {soma_curriculo})"
            )

        soma_final = round(
            self.peso_curriculo + self.peso_entrevista_rh + self.peso_entrevista_tec,
            10
        )
        if soma_final != 1.0:
            raise ValueError(
                f"peso_curriculo + peso_entrevista_rh + peso_entrevista_tec "
                f"deve ser 1.0 (atual: {soma_final})"
            )
        return self


class VagaUpdateRequisitos(BaseModel):
    """Nome e/ou requisitos — qualquer campo omitido é ignorado."""
    nome             : str | None = Field(None, min_length=1, max_length=200)
    requisitos_texto : str | None = Field(None, min_length=1, max_length=20_000)

    @field_validator("nome", "requisitos_texto", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v
