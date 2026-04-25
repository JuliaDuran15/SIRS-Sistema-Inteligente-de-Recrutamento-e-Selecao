from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.api.deps import DB
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.candidato import Candidato
from app.models.vaga import Vaga
from app.schemas.candidatura import CandidaturaCreate, CandidaturaResponse

router = APIRouter()

TRANSICOES = {
    StatusCandidatura.NOVO:                     [StatusCandidatura.AGUARDANDO_PROC],
    StatusCandidatura.AGUARDANDO_PROC:          [StatusCandidatura.PROCESSANDO],
    StatusCandidatura.PROCESSANDO:              [StatusCandidatura.TRIAGEM_PENDENTE],
    StatusCandidatura.TRIAGEM_PENDENTE:         [StatusCandidatura.APROVADO_TRIAGEM,
                                                 StatusCandidatura.REPROVADO_TRIAGEM],
    StatusCandidatura.APROVADO_TRIAGEM:         [StatusCandidatura.ENTREVISTA_RH_AGENDADA],
    StatusCandidatura.ENTREVISTA_RH_AGENDADA:   [StatusCandidatura.ENTREVISTA_RH_REALIZADA],
    StatusCandidatura.ENTREVISTA_RH_REALIZADA:  [StatusCandidatura.ENTREVISTA_TEC_AGENDADA,
                                                 StatusCandidatura.REPROVADO_RH],
    StatusCandidatura.ENTREVISTA_TEC_AGENDADA:  [StatusCandidatura.ENTREVISTA_TEC_REALIZADA],
    StatusCandidatura.ENTREVISTA_TEC_REALIZADA: [StatusCandidatura.DECISAO_PENDENTE,
                                                 StatusCandidatura.REPROVADO_TECNICO],
    StatusCandidatura.DECISAO_PENDENTE:         [StatusCandidatura.CONTRATADO,
                                                 StatusCandidatura.NAO_APROVADO,
                                                 StatusCandidatura.BANCO_TALENTOS],
    StatusCandidatura.REPROVADO_TRIAGEM:        [StatusCandidatura.BANCO_TALENTOS],
    StatusCandidatura.REPROVADO_RH:             [StatusCandidatura.BANCO_TALENTOS],
    StatusCandidatura.REPROVADO_TECNICO:        [StatusCandidatura.BANCO_TALENTOS],
}

def transicionar(candidatura: Candidatura, novo_status: StatusCandidatura, ator: str = "sistema"):
    permitidos = TRANSICOES.get(candidatura.status, [])
    if novo_status not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {candidatura.status} → {novo_status}"
        )
    historico = candidatura.historico or []
    historico.append({
        "de"  : candidatura.status,
        "para": novo_status,
        "ator": ator,
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status    = novo_status


@router.post("/", response_model=CandidaturaResponse, status_code=201)
def criar_candidatura(dados: CandidaturaCreate, db: Session = DB):
    if not db.query(Candidato).filter(Candidato.id == dados.candidato_id).first():
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    if not db.query(Vaga).filter(Vaga.id == dados.vaga_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    candidatura = Candidatura(
        candidato_id=dados.candidato_id,
        vaga_id=dados.vaga_id,
        historico=[],
    )
    db.add(candidatura)
    db.commit()
    db.refresh(candidatura)
    return candidatura


@router.get("/", response_model=list[CandidaturaResponse])
def listar_candidaturas(vaga_id: str | None = None, db: Session = DB):
    query = db.query(Candidatura)
    if vaga_id:
        query = query.filter(Candidatura.vaga_id == vaga_id)
    return query.all()


@router.get("/{candidatura_id}", response_model=CandidaturaResponse)
def buscar_candidatura(candidatura_id: str, db: Session = DB):
    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")
    return candidatura


@router.patch("/{candidatura_id}/status", response_model=CandidaturaResponse)
def atualizar_status(candidatura_id: str, novo_status: StatusCandidatura,
                     ator: str = "rh", db: Session = DB):
    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    transicionar(candidatura, novo_status, ator)
    db.commit()
    db.refresh(candidatura)
    return candidatura