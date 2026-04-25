from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.api.deps import DB
from app.models.entrevista import Entrevista
from app.models.candidatura import Candidatura, StatusCandidatura
from app.schemas.entrevista import EntrevistaCreate, EntrevistaResultado, EntrevistaResponse

router = APIRouter()

STATUS_APOS_AGENDAR = {
    "rh":      StatusCandidatura.ENTREVISTA_RH_AGENDADA,
    "tecnica": StatusCandidatura.ENTREVISTA_TEC_AGENDADA,
}
STATUS_APOS_REALIZAR = {
    "rh":      StatusCandidatura.ENTREVISTA_RH_REALIZADA,
    "tecnica": StatusCandidatura.ENTREVISTA_TEC_REALIZADA,
}

@router.post("/", response_model=EntrevistaResponse, status_code=201)
def agendar_entrevista(dados: EntrevistaCreate, db: Session = DB):
    if dados.tipo not in ("rh", "tecnica"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'rh' ou 'tecnica'")

    candidatura = db.query(Candidatura).filter(Candidatura.id == dados.candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    entrevista = Entrevista(
        candidatura_id   = dados.candidatura_id,
        entrevistador_id = dados.entrevistador_id,
        tipo             = dados.tipo,
        agendada_para    = dados.agendada_para,
        status           = "agendada",
    )
    db.add(entrevista)

    # avança o status da candidatura automaticamente
    from app.api.endpoints.candidaturas import transicionar
    transicionar(candidatura, STATUS_APOS_AGENDAR[dados.tipo], ator="sistema")

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.patch("/{entrevista_id}/resultado", response_model=EntrevistaResponse)
def registrar_resultado(entrevista_id: str, dados: EntrevistaResultado, db: Session = DB):
    entrevista = db.query(Entrevista).filter(Entrevista.id == entrevista_id).first()
    if not entrevista:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada")
    if entrevista.status == "realizada":
        raise HTTPException(status_code=400, detail="Entrevista já foi registrada")
    if dados.score_manual < 0 or dados.score_manual > 10:
        raise HTTPException(status_code=400, detail="Score deve ser entre 0 e 10")

    entrevista.score_manual  = dados.score_manual
    entrevista.anotacoes     = dados.anotacoes
    entrevista.pontos_fortes = dados.pontos_fortes
    entrevista.pontos_fracos = dados.pontos_fracos
    entrevista.status        = "realizada"
    entrevista.realizada_em  = datetime.utcnow()

    # avança o status da candidatura
    candidatura = db.query(Candidatura).filter(
        Candidatura.id == entrevista.candidatura_id
    ).first()

    from app.api.endpoints.candidaturas import transicionar
    transicionar(candidatura, STATUS_APOS_REALIZAR[entrevista.tipo], ator="entrevistador")

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.get("/candidatura/{candidatura_id}", response_model=list[EntrevistaResponse])
def listar_por_candidatura(candidatura_id: str, db: Session = DB):
    return db.query(Entrevista).filter(
        Entrevista.candidatura_id == candidatura_id
    ).order_by(Entrevista.agendada_para).all()