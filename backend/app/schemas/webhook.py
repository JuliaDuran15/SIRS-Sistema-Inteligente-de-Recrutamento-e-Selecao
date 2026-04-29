"""Schemas de entrada e saída para o webhook de importação."""
from datetime import date
from pydantic import BaseModel


class FormacaoImport(BaseModel):
    curso         : str
    instituicao   : str
    nivel         : str = "graduacao"
    status        : str = "concluido"
    ano_conclusao : int | None = None


class VagaImport(BaseModel):
    external_id      : str | None = None
    nome             : str
    requisitos_texto : str


class CandidatoImport(BaseModel):
    external_id     : str | None = None
    nome            : str
    email           : str   # validado individualmente no processamento para suportar erros parciais
    telefone        : str | None = None
    data_nascimento : date | None = None
    logradouro      : str | None = None
    bairro          : str | None = None
    cidade          : str | None = None
    estado          : str | None = None
    cep             : str | None = None
    formacao        : list[FormacaoImport] = []
    curriculo_texto : str | None = None
    # Referências para vincular a uma vaga
    vaga_external_id : str | None = None   # referencia VagaImport.external_id no mesmo payload
    vaga_nome        : str | None = None   # fallback: busca por nome no banco


class ImportacaoPayload(BaseModel):
    """Envelope completo aceito pelo endpoint /webhook/importar (JSON)."""
    fonte      : str | None = None
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
