from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, model_validator


class VagaCreate(BaseModel):
    nome             : str
    requisitos_texto : str
    gestores_ids     : list[str] = []

    # Pesos do score curricular — devem somar 1.0
    peso_rh      : float = 0.6
    peso_mercado : float = 0.4

    # Pesos do score consolidado final — devem somar 1.0
    peso_curriculo      : float = 0.50
    peso_entrevista_rh  : float = 0.25
    peso_entrevista_tec : float = 0.25

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
    peso_rh             : float
    peso_mercado        : float
    peso_curriculo      : float
    peso_entrevista_rh  : float
    peso_entrevista_tec : float

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
    """
    Usado quando o analista edita só o texto dos requisitos.
    O sistema recalcula o vetor automaticamente.
    """
    requisitos_texto: str