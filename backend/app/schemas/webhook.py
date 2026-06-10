"""Schemas de entrada e saída para o webhook de importação."""
from datetime import date
from pydantic import BaseModel, Field, field_validator


class FormacaoImport(BaseModel):
    curso         : str           = Field(..., min_length=1, max_length=200)
    instituicao   : str           = Field(..., min_length=1, max_length=200)
    nivel         : str           = Field("graduacao", max_length=50)
    status        : str           = Field("concluido", max_length=50)
    ano_conclusao : int | None    = Field(None, ge=1900, le=2100)


class VagaImport(BaseModel):
    external_id      : str | None = Field(None, max_length=100)
    nome             : str        = Field(..., min_length=1, max_length=200)
    requisitos_texto : str        = Field(..., min_length=1, max_length=20_000)

    @field_validator("nome", "requisitos_texto", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v


class CandidatoImport(BaseModel):
    external_id     : str | None  = Field(None, max_length=100)
    nome            : str         = Field(..., min_length=1, max_length=200)
    email           : str         = Field(..., max_length=254)
    # email validado individualmente no processamento para suportar erros parciais
    telefone        : str | None  = Field(None, max_length=30)
    data_nascimento : date | None = None
    logradouro      : str | None  = Field(None, max_length=200)
    bairro          : str | None  = Field(None, max_length=100)
    cidade          : str | None  = Field(None, max_length=100)
    estado          : str | None  = Field(None, max_length=2)
    cep             : str | None  = Field(None, max_length=10)
    formacao        : list[FormacaoImport] = []
    curriculo_texto : str | None  = Field(None, max_length=100_000)
    # Referências para vincular a uma vaga
    vaga_external_id : str | None = Field(None, max_length=100)
    vaga_nome        : str | None = Field(None, max_length=200)

    @field_validator("nome", "email", "telefone", "logradouro", "bairro",
                     "cidade", "estado", "cep", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v


class ImportacaoPayload(BaseModel):
    """Envelope completo aceito pelo endpoint /webhook/importar (JSON)."""
    fonte      : str | None = Field(None, max_length=100)
    vagas      : list[VagaImport] = []
    candidatos : list[CandidatoImport] = []


class ImportacaoResultado(BaseModel):
    vagas_criadas           : int = 0
    candidatos_criados      : int = 0
    candidatos_atualizados  : int = 0
    candidaturas_criadas    : int = 0
    curriculos_processados  : int = 0


class ErroImportacao(BaseModel):
    tipo          : str           # "vaga" | "candidato"
    identificador : str | None    # external_id ou e-mail
    detalhe       : str


class ImportacaoResponse(BaseModel):
    importados  : ImportacaoResultado
    erros       : list[ErroImportacao]
    total_erros : int
