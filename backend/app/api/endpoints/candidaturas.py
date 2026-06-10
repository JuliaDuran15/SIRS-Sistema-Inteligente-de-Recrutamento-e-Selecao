import shutil
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path

from app.api.deps import DB
from app.core.auth import APENAS_ADMIN, QUALQUER_PAPEL, RH_OU_ADMIN, get_usuario_atual
from app.core.config import settings
from app.models.candidato import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.vaga import Vaga
from app.schemas.candidatura import CandidaturaCreate, CandidaturaResponse, CurriculoDetalhado
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()

TRANSICOES = {
    StatusCandidatura.NOVO:                     [StatusCandidatura.AGUARDANDO_PROC],
    StatusCandidatura.AGUARDANDO_PROC:          [StatusCandidatura.PROCESSANDO],
    StatusCandidatura.PROCESSANDO:              [StatusCandidatura.TRIAGEM_PENDENTE],
    StatusCandidatura.TRIAGEM_PENDENTE:         [StatusCandidatura.APROVADO_TRIAGEM,
                                                 StatusCandidatura.REPROVADO_TRIAGEM,
                                                 StatusCandidatura.BANCO_TALENTOS],
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
    historico = list(candidatura.historico or [])
    historico.append({
        "de"  : candidatura.status,
        "para": novo_status,
        "ator": ator,
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status    = novo_status


@router.post("/", response_model=CandidaturaResponse, status_code=201)
def criar_candidatura(dados: CandidaturaCreate, db: Session = DB, _=RH_OU_ADMIN):
    if not db.query(Candidato).filter(Candidato.id == dados.candidato_id).first():
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    if not db.query(Vaga).filter(Vaga.id == dados.vaga_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    candidatura = Candidatura(
        candidato_id=dados.candidato_id,
        vaga_id=dados.vaga_id,
        historico=[],
        origem="manual",
    )
    db.add(candidatura)
    db.commit()
    db.refresh(candidatura)
    return candidatura


@router.get("/", response_model=list[CandidaturaResponse])
def listar_candidaturas(
    vaga_id      : str | None = None,
    candidato_id : str | None = None,
    db: Session = DB,
    _=QUALQUER_PAPEL,
):
    query = db.query(Candidatura)
    if vaga_id:
        query = query.filter(Candidatura.vaga_id == vaga_id)
    if candidato_id:
        query = query.filter(Candidatura.candidato_id == candidato_id)
    return query.all()


@router.get("/{candidatura_id}", response_model=CandidaturaResponse)
def buscar_candidatura(candidatura_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")
    return candidatura


UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/{candidatura_id}/curriculo", response_model=CandidaturaResponse)
def upload_curriculo(candidatura_id: str, arquivo: UploadFile = File(...),
                     db: Session = DB, _=RH_OU_ADMIN):
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")

    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    nome_arquivo = f"{uuid_lib.uuid4()}.pdf"
    caminho      = UPLOAD_DIR / nome_arquivo

    with caminho.open("wb") as f:
        shutil.copyfileobj(arquivo.file, f)

    # Registra o nome do arquivo no curriculo para poder servir depois
    curriculo = db.query(Curriculo).filter(Curriculo.candidatura_id == candidatura_id).first()
    if not curriculo:
        curriculo = Curriculo(candidatura_id=candidatura_id)
        db.add(curriculo)
    curriculo.arquivo_pdf = nome_arquivo

    historico = list(candidatura.historico or [])
    historico.append({
        "de"  : candidatura.status,
        "para": StatusCandidatura.AGUARDANDO_PROC,
        "ator": "sistema",
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status = StatusCandidatura.AGUARDANDO_PROC
    db.commit()

    from app.ai.tasks import processar_curriculo
    processar_curriculo.delay(str(candidatura_id), str(caminho))

    db.refresh(candidatura)
    return candidatura


class CurriculoTextoInput(BaseModel):
    texto: str


@router.post("/{candidatura_id}/curriculo/texto", response_model=CandidaturaResponse)
def upload_curriculo_texto(
    candidatura_id: str,
    dados: CurriculoTextoInput,
    db: Session = DB,
    _=RH_OU_ADMIN,
):
    if not dados.texto.strip():
        raise HTTPException(status_code=400, detail="Texto do currículo não pode estar vazio")

    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    curriculo = db.query(Curriculo).filter(Curriculo.candidatura_id == candidatura_id).first()
    if not curriculo:
        curriculo = Curriculo(candidatura_id=candidatura_id)
        db.add(curriculo)

    historico = list(candidatura.historico or [])
    historico.append({
        "de"  : candidatura.status,
        "para": StatusCandidatura.AGUARDANDO_PROC,
        "ator": "sistema",
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status = StatusCandidatura.AGUARDANDO_PROC
    db.commit()

    from app.ai.tasks import processar_curriculo_texto
    processar_curriculo_texto.delay(str(candidatura_id), dados.texto)

    db.refresh(candidatura)
    return candidatura


@router.get("/{candidatura_id}/curriculo", response_model=CurriculoDetalhado)
def get_curriculo(candidatura_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    curriculo = db.query(Curriculo).filter(
        Curriculo.candidatura_id == candidatura_id
    ).first()
    if not curriculo:
        raise HTTPException(status_code=404, detail="Currículo não encontrado para esta candidatura")
    return curriculo


@router.get("/{candidatura_id}/curriculo/pdf")
def servir_pdf(candidatura_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    curriculo = db.query(Curriculo).filter(
        Curriculo.candidatura_id == candidatura_id
    ).first()
    if not curriculo or not curriculo.arquivo_pdf:
        raise HTTPException(status_code=404, detail="PDF não disponível para esta candidatura")
    caminho = UPLOAD_DIR / curriculo.arquivo_pdf
    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado no servidor")
    return FileResponse(
        path=str(caminho),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


_TRIAGEM_DESTINOS = {
    StatusCandidatura.APROVADO_TRIAGEM,
    StatusCandidatura.REPROVADO_TRIAGEM,
    StatusCandidatura.BANCO_TALENTOS,
}


class TriagemEmLoteRequest(BaseModel):
    candidatura_ids : list[str]
    novo_status     : StatusCandidatura
    ator            : str = "rh"


class TriagemEmLoteResponse(BaseModel):
    atualizadas : int
    erros       : list[dict]


@router.post("/triagem-em-lote", response_model=TriagemEmLoteResponse)
def triagem_em_lote(
    dados   : TriagemEmLoteRequest,
    db      : Session = DB,
    usuario = Depends(get_usuario_atual),
):
    """Aplica o mesmo status de triagem a múltiplas candidaturas de uma vez.
    Só é permitido para transições de triagem:
    triagem_pendente → aprovado_triagem | reprovado_triagem | banco_de_talentos."""
    from app.models.usuario import PapelUsuario

    if usuario.papel not in (PapelUsuario.RH, PapelUsuario.ADMIN):
        raise HTTPException(status_code=403, detail="Apenas RH ou Admin pode fazer triagem em lote")
    if dados.novo_status not in _TRIAGEM_DESTINOS:
        raise HTTPException(
            status_code=400,
            detail="Ação em lote só disponível para triagem (aprovado_triagem / reprovado_triagem / banco_de_talentos)",
        )

    atualizadas = 0
    erros: list[dict] = []

    for cid in dados.candidatura_ids:
        sp = db.begin_nested()
        try:
            candidatura = db.query(Candidatura).filter(Candidatura.id == cid).first()
            if not candidatura:
                erros.append({"id": cid, "detalhe": "Não encontrada"})
                sp.rollback()
                continue
            transicionar(candidatura, dados.novo_status, ator=dados.ator)
            sp.commit()
            atualizadas += 1
        except Exception as exc:
            sp.rollback()
            erros.append({"id": cid, "detalhe": str(exc)})

    db.commit()
    return TriagemEmLoteResponse(atualizadas=atualizadas, erros=erros)


@router.patch("/{candidatura_id}/status", response_model=CandidaturaResponse)
def atualizar_status(
    candidatura_id: str,
    novo_status    : StatusCandidatura,
    ator           : str = "rh",
    db             : Session = DB,
    usuario=Depends(get_usuario_atual),
):
    from app.models.usuario import PapelUsuario

    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    if usuario.papel == PapelUsuario.GESTOR:
        # Gestor só pode tomar a decisão final nas vagas onde está atribuído
        if candidatura.status != StatusCandidatura.DECISAO_PENDENTE:
            raise HTTPException(
                status_code=403,
                detail="Gestor só pode tomar a decisão final (contratado / não aprovado / banco de talentos)",
            )
        vaga = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()
        if not vaga or str(usuario.id) not in (vaga.gestores_ids or []):
            raise HTTPException(status_code=403, detail="Você não é gestor desta vaga")
    elif usuario.papel not in (PapelUsuario.RH, PapelUsuario.ADMIN):
        raise HTTPException(status_code=403, detail="Acesso negado")

    transicionar(candidatura, novo_status, ator)
    db.commit()
    db.refresh(candidatura)

    if novo_status in (StatusCandidatura.APROVADO_TRIAGEM, StatusCandidatura.REPROVADO_TRIAGEM):
        from app.core.email import email_triagem_resultado
        from app.models.candidato import Candidato
        candidato = db.query(Candidato).filter(Candidato.id == candidatura.candidato_id).first()
        vaga_obj  = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()
        if candidato and vaga_obj:
            email_triagem_resultado(
                destinatario   = usuario.email,
                nome_rh        = usuario.nome,
                candidato_nome = candidato.nome,
                vaga_nome      = vaga_obj.nome,
                aprovado       = (novo_status == StatusCandidatura.APROVADO_TRIAGEM),
            )

    return candidatura


@router.delete("/{candidatura_id}", status_code=204)
def desvincular_candidatura(
    candidatura_id: str,
    db: Session = DB,
    _=APENAS_ADMIN,
):
    """Remove a candidatura e todos os seus dados associados (currículo, entrevistas).
    Exclusivo para Admin — usar apenas para corrigir erros de vínculo."""
    candidatura = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
    if not candidatura:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    from app.models.entrevista import Entrevista
    db.query(Entrevista).filter(Entrevista.candidatura_id == candidatura_id).delete()
    db.query(Curriculo).filter(Curriculo.candidatura_id == candidatura_id).delete()
    db.delete(candidatura)
    db.commit()
