from datetime import datetime

from app.api.deps import DB
from app.core.auth import APENAS_ADMIN, QUALQUER_PAPEL, RH_OU_ADMIN, get_usuario_atual
from app.models.candidato import Candidato
from app.models.candidatura import Candidatura
from app.models.usuario import PapelUsuario
from app.models.vaga import Vaga
from app.schemas.candidato import (
    AlterarEmailRequest,
    CandidatoCreate,
    CandidatoListResponse,
    CandidatoResponse,
    CandidatoUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/", response_model=CandidatoResponse, status_code=201)
def criar_candidato(dados: CandidatoCreate, db: Session = DB, _=RH_OU_ADMIN):
    existe = db.query(Candidato).filter(Candidato.email == dados.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    payload = dados.model_dump()
    payload["formacao"] = [f.model_dump() for f in dados.formacao]
    candidato = Candidato(**payload)
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.post("/webhook", response_model=CandidatoResponse, status_code=201)
def webhook_candidato(dados: CandidatoCreate, db: Session = DB):
    """Recebe candidatos vindos de sistemas externos — sem autenticação.
    Para importação completa (vagas + candidaturas), use POST /webhook/importar."""
    existe = db.query(Candidato).filter(Candidato.email == dados.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    payload = dados.model_dump()
    payload["formacao"] = [f.model_dump() for f in dados.formacao]
    candidato = Candidato(**payload)
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.get("/", response_model=CandidatoListResponse)
def listar_candidatos(
    q      : str | None = Query(None, description="Busca por nome ou e-mail", max_length=200),
    cidade : str | None = Query(None, max_length=100),
    origem : str | None = Query(None, description="manual | externo", max_length=50),
    limit  : int        = Query(50, ge=1, le=200),
    offset : int        = Query(0,  ge=0),
    db     : Session    = DB,
    usuario             = Depends(get_usuario_atual),
):
    query = db.query(Candidato)

    # Filtra por papel
    if usuario.papel == PapelUsuario.GESTOR:
        uid = str(usuario.id)
        vaga_ids = (
            db.query(Vaga.id)
            .filter(Vaga.gestores_ids.contains([uid]))
            .scalar_subquery()
        )
        candidato_ids = (
            db.query(Candidatura.candidato_id)
            .filter(Candidatura.vaga_id.in_(vaga_ids))
            .distinct()
            .scalar_subquery()
        )
        query = query.filter(Candidato.id.in_(candidato_ids))

    # Busca por nome ou e-mail
    if q:
        termo = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Candidato.nome.ilike(termo),
                Candidato.email.ilike(termo),
            )
        )

    # Filtros adicionais
    if cidade:
        query = query.filter(Candidato.cidade.ilike(f"%{cidade}%"))
    if origem:
        from app.models.candidatura import Candidatura as Cand
        candidato_ids_origem = (
            db.query(Cand.candidato_id)
            .filter(Cand.origem == origem)
            .distinct()
            .scalar_subquery()
        )
        query = query.filter(Candidato.id.in_(candidato_ids_origem))

    total = query.count()
    candidatos_raw = (
        query.order_by(Candidato.criado_em.desc())
             .limit(limit)
             .offset(offset)
             .all()
    )

    # Identifica quais candidatos têm pelo menos uma candidatura externa
    ids = [str(c.id) for c in candidatos_raw]
    externos = set(
        str(cid) for (cid,) in db.query(Candidatura.candidato_id)
            .filter(
                Candidatura.candidato_id.in_(ids),
                Candidatura.origem == "externo",
            )
            .distinct()
            .all()
    ) if ids else set()

    items = []
    for c in candidatos_raw:
        d = CandidatoResponse.model_validate(c)
        d.tem_candidatura_externa = str(c.id) in externos
        items.append(d)

    return CandidatoListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{candidato_id}", response_model=CandidatoResponse)
def buscar_candidato(candidato_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    return candidato


@router.patch("/{candidato_id}/email", response_model=CandidatoResponse)
def alterar_email_candidato(
    candidato_id : str,
    dados        : AlterarEmailRequest,
    db           : Session = DB,
    usuario      = APENAS_ADMIN,
):
    """Apenas admin pode alterar o e-mail de um candidato. A alteração é registrada na auditoria."""
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")

    email_novo = str(dados.email_novo).lower()
    if email_novo == candidato.email.lower():
        raise HTTPException(status_code=400, detail="O novo e-mail é igual ao e-mail atual")

    conflito = db.query(Candidato).filter(Candidato.email == email_novo).first()
    if conflito:
        raise HTTPException(status_code=400, detail="Este e-mail já está em uso por outro candidato")

    email_anterior   = candidato.email
    candidato.email  = email_novo

    novo_hist = list(candidato.historico or [])
    novo_hist.append({
        "tipo"           : "alteracao_email",
        "email_anterior" : email_anterior,
        "email_novo"     : email_novo,
        "ator"           : usuario.nome,
        "em"             : datetime.utcnow().isoformat(),
    })
    candidato.historico = novo_hist

    db.commit()
    db.refresh(candidato)
    return candidato


@router.patch("/{candidato_id}", response_model=CandidatoResponse)
def atualizar_candidato(candidato_id: str, dados: CandidatoUpdate, db: Session = DB, _=RH_OU_ADMIN):
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo == "formacao" and valor is not None:
            valor = [f if isinstance(f, dict) else f.model_dump() for f in valor]
        setattr(candidato, campo, valor)
    db.commit()
    db.refresh(candidato)
    return candidato
