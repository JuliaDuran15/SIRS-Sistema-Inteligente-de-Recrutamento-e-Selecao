from datetime import datetime

from app.api.deps import DB
from app.core.auth import QUALQUER_PAPEL, get_usuario_atual
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.entrevista import Entrevista
from app.models.usuario import PapelUsuario
from app.schemas.entrevista import EntrevistaCreate, EntrevistaResponse, EntrevistaResultado
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()

STATUS_APOS_AGENDAR = {
    "rh":      StatusCandidatura.ENTREVISTA_RH_AGENDADA,
    "tecnica": StatusCandidatura.ENTREVISTA_TEC_AGENDADA,
}
STATUS_APOS_REALIZAR = {
    "rh":      StatusCandidatura.ENTREVISTA_RH_REALIZADA,
    "tecnica": StatusCandidatura.ENTREVISTA_TEC_REALIZADA,
}

def _checar_agendamento(usuario):
    """Só RH ou Admin podem agendar entrevistas."""
    if usuario.papel not in (PapelUsuario.RH, PapelUsuario.ADMIN):
        raise HTTPException(status_code=403, detail="Apenas RH ou Admin pode agendar entrevistas")


def _checar_registro_resultado(tipo: str, usuario):
    """RH registra resultado de entrevistas RH; Gestor registra resultado das técnicas; Admin faz tudo."""
    if usuario.papel == PapelUsuario.ADMIN:
        return
    if tipo == "rh" and usuario.papel != PapelUsuario.RH:
        raise HTTPException(status_code=403, detail="Apenas RH ou Admin pode registrar resultado de entrevistas de RH")
    if tipo == "tecnica" and usuario.papel != PapelUsuario.GESTOR:
        raise HTTPException(status_code=403, detail="Apenas Gestor técnico ou Admin pode registrar resultado de entrevistas técnicas")


@router.post("/", response_model=EntrevistaResponse, status_code=201)
def agendar_entrevista(
    dados: EntrevistaCreate,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    if dados.tipo not in ("rh", "tecnica"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'rh' ou 'tecnica'")

    _checar_agendamento(usuario)

    candidatura = db.query(Candidatura).filter(Candidatura.id == dados.candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    entrevista = Entrevista(
        candidatura_id   = dados.candidatura_id,
        entrevistador_id = usuario.id,
        tipo             = dados.tipo,
        agendada_para    = dados.agendada_para,
        status           = "agendada",
    )
    db.add(entrevista)

    from app.api.endpoints.candidaturas import transicionar
    transicionar(candidatura, STATUS_APOS_AGENDAR[dados.tipo], ator=usuario.nome)

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.patch("/{entrevista_id}/resultado", response_model=EntrevistaResponse)
def registrar_resultado(
    entrevista_id: str,
    dados: EntrevistaResultado,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    entrevista = db.query(Entrevista).filter(Entrevista.id == entrevista_id).first()
    if not entrevista:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada")
    if entrevista.status == "realizada":
        raise HTTPException(status_code=400, detail="Entrevista já foi registrada")
    if dados.score_manual < 0 or dados.score_manual > 10:
        raise HTTPException(status_code=400, detail="Score deve ser entre 0 e 10")

    _checar_registro_resultado(entrevista.tipo, usuario)

    entrevista.score_manual  = dados.score_manual
    entrevista.anotacoes     = dados.anotacoes
    entrevista.pontos_fortes = dados.pontos_fortes
    entrevista.pontos_fracos = dados.pontos_fracos
    entrevista.status        = "realizada"
    entrevista.realizada_em  = datetime.utcnow()

    candidatura = db.query(Candidatura).filter(
        Candidatura.id == entrevista.candidatura_id
    ).first()

    from app.api.endpoints.candidaturas import transicionar
    transicionar(candidatura, STATUS_APOS_REALIZAR[entrevista.tipo], ator=usuario.nome)

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.get("/candidatura/{candidatura_id}", response_model=list[EntrevistaResponse])
def listar_por_candidatura(candidatura_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    return db.query(Entrevista).filter(
        Entrevista.candidatura_id == candidatura_id
    ).order_by(Entrevista.agendada_para).all()
