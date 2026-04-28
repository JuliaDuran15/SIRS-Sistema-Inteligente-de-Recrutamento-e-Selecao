from datetime import datetime

from app.api.deps import DB
from app.core.auth import QUALQUER_PAPEL, get_usuario_atual
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.entrevista import Entrevista
from app.models.usuario import PapelUsuario
from app.models.vaga import Vaga
from app.schemas.entrevista import AnotacoesUpdate, EntrevistaCreate, EntrevistaResponse, EntrevistaResultado
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
    if entrevista.status not in ("agendada", "realizada"):
        raise HTTPException(status_code=400, detail="Entrevista não pode ser editada")
    if dados.score_manual < 0 or dados.score_manual > 10:
        raise HTTPException(status_code=400, detail="Score deve ser entre 0 e 10")

    _checar_registro_resultado(entrevista.tipo, usuario)

    ja_realizada = entrevista.status == "realizada"

    if ja_realizada:
        # Re-edição: grava histórico completo, não avança candidatura
        historico = list(entrevista.historico_edicoes or [])
        historico.append({
            "score_anterior": entrevista.score_manual,
            "texto_anterior": entrevista.anotacoes,
            "editado_em"    : datetime.utcnow().isoformat(),
            "editado_por"   : usuario.nome,
        })
        entrevista.historico_edicoes = historico

    entrevista.score_manual  = dados.score_manual
    entrevista.anotacoes     = dados.anotacoes
    entrevista.pontos_fortes = dados.pontos_fortes
    entrevista.pontos_fracos = dados.pontos_fracos

    if not ja_realizada:
        # Primeira vez: define status e avança candidatura
        entrevista.status       = "realizada"
        entrevista.realizada_em = datetime.utcnow()

        candidatura = db.query(Candidatura).filter(
            Candidatura.id == entrevista.candidatura_id
        ).first()
        from app.api.endpoints.candidaturas import transicionar
        transicionar(candidatura, STATUS_APOS_REALIZAR[entrevista.tipo], ator=usuario.nome)

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.patch("/{entrevista_id}/anotacoes", response_model=EntrevistaResponse)
def editar_anotacoes(
    entrevista_id: str,
    dados: AnotacoesUpdate,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    """
    RH edita anotações de entrevistas de RH.
    Gestor atribuído à vaga edita anotações de entrevistas técnicas.
    Admin edita qualquer entrevista.
    Cada edição fica registrada no histórico.
    """
    entrevista = db.query(Entrevista).filter(Entrevista.id == entrevista_id).first()
    if not entrevista:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada")
    if entrevista.status != "realizada":
        raise HTTPException(status_code=400, detail="Só é possível editar anotações de entrevistas realizadas")

    if usuario.papel != PapelUsuario.ADMIN:
        if entrevista.tipo == "rh" and usuario.papel != PapelUsuario.RH:
            raise HTTPException(status_code=403, detail="Apenas RH ou Admin pode editar anotações de entrevistas de RH")
        if entrevista.tipo == "tecnica" and usuario.papel != PapelUsuario.GESTOR:
            raise HTTPException(status_code=403, detail="Apenas Gestor técnico ou Admin pode editar anotações de entrevistas técnicas")
        if entrevista.tipo == "tecnica":
            candidatura = db.query(Candidatura).filter(Candidatura.id == entrevista.candidatura_id).first()
            vaga = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()
            if str(usuario.id) not in (vaga.gestores_ids or []):
                raise HTTPException(status_code=403, detail="Você não é gestor desta vaga")

    historico = list(entrevista.historico_edicoes or [])
    historico.append({
        "texto_anterior": entrevista.anotacoes,
        "editado_em"    : datetime.utcnow().isoformat(),
        "editado_por"   : usuario.nome,
    })
    entrevista.historico_edicoes = historico
    entrevista.anotacoes = dados.anotacoes

    db.commit()
    db.refresh(entrevista)
    return entrevista


@router.get("/candidatura/{candidatura_id}", response_model=list[EntrevistaResponse])
def listar_por_candidatura(candidatura_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    return db.query(Entrevista).filter(
        Entrevista.candidatura_id == candidatura_id
    ).order_by(Entrevista.agendada_para).all()
