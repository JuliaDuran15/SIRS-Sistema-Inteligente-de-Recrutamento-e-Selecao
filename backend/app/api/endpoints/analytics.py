"""
Endpoints de analytics — funil, scores, resumo.
Dados filtrados pelas vagas visíveis ao usuário logado:
  Admin  → todos
  RH     → vagas onde é criador ou está em rhs_autorizados
  Gestor → vagas onde está em gestores_ids
"""
from app.api.deps import DB
from app.core.auth import get_usuario_atual
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.candidato import Candidato
from app.models.curriculo import Curriculo
from app.models.entrevista import Entrevista
from app.models.usuario import PapelUsuario
from app.models.vaga import Vaga
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class EtapaFunil(BaseModel):
    status     : str
    label      : str
    quantidade : int
    cor        : str


class FunilResponse(BaseModel):
    vaga_id   : str | None
    vaga_nome : str | None
    etapas    : list[EtapaFunil]
    total     : int


class ResumoGeral(BaseModel):
    vagas_abertas          : int
    vagas_pausadas         : int
    candidatos_total       : int
    candidaturas_ativas    : int
    em_triagem             : int
    entrevistas_agendadas  : int
    decisoes_pendentes     : int
    contratados_total      : int


class BucketScore(BaseModel):
    faixa      : str
    quantidade : int


class DistribuicaoScores(BaseModel):
    vaga_id  : str
    buckets  : list[BucketScore]
    media    : float | None
    mediana  : float | None


# ── Labels e cores ────────────────────────────────────────────────────────────

_ETAPAS_FUNIL = [
    ("novo",                     "Novos",                "gray"),
    ("triagem_pendente",         "Triagem pendente",     "amber"),
    ("aprovado_triagem",         "Aprovados triagem",    "blue"),
    ("reprovado_triagem",        "Reprovados triagem",   "red"),
    ("entrevista_rh_agendada",   "Entrev. RH agendada",  "blue"),
    ("entrevista_rh_realizada",  "Entrev. RH realizada", "blue"),
    ("reprovado_rh",             "Reprovados RH",        "red"),
    ("entrevista_tec_agendada",  "Entrev. Téc. agendada","blue"),
    ("entrevista_tec_realizada", "Entrev. Téc. realizada","blue"),
    ("reprovado_tecnico",        "Reprovados técnico",   "red"),
    ("decisao_pendente",         "Decisão pendente",     "amber"),
    ("contratado",               "Contratados",          "green"),
    ("nao_aprovado",             "Não aprovados",        "red"),
    ("banco_de_talentos",        "Banco de talentos",    "purple"),
]

_STATUSES_ATIVOS = {
    StatusCandidatura.TRIAGEM_PENDENTE,
    StatusCandidatura.APROVADO_TRIAGEM,
    StatusCandidatura.ENTREVISTA_RH_AGENDADA,
    StatusCandidatura.ENTREVISTA_RH_REALIZADA,
    StatusCandidatura.ENTREVISTA_TEC_AGENDADA,
    StatusCandidatura.ENTREVISTA_TEC_REALIZADA,
    StatusCandidatura.DECISAO_PENDENTE,
}


# ── Helper: IDs das vagas visíveis ao usuário ─────────────────────────────────

def _vagas_ids_query(usuario, db: Session):
    """Retorna subquery com os IDs das vagas visíveis ao usuário."""
    q = db.query(Vaga.id)
    uid = str(usuario.id)
    if usuario.papel == PapelUsuario.GESTOR:
        q = q.filter(Vaga.gestores_ids.contains([uid]))
    elif usuario.papel == PapelUsuario.RH:
        q = q.filter(
            or_(
                Vaga.rhs_autorizados == None,
                Vaga.rhs_autorizados.contains([uid]),
            )
        )
    # Admin: todas as vagas (sem filtro adicional)
    return q.scalar_subquery()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/resumo", response_model=ResumoGeral)
def resumo_geral(db: Session = DB, usuario=Depends(get_usuario_atual)):
    """Resumo executivo filtrado pelas vagas do usuário."""
    vaga_ids = _vagas_ids_query(usuario, db)

    cands_query = db.query(Candidatura).filter(Candidatura.vaga_id.in_(vaga_ids))

    return ResumoGeral(
        vagas_abertas         = db.query(Vaga).filter(
                                    Vaga.id.in_(vaga_ids), Vaga.status == "aberta"
                                ).count(),
        vagas_pausadas        = db.query(Vaga).filter(
                                    Vaga.id.in_(vaga_ids), Vaga.status == "pausada"
                                ).count(),
        candidatos_total      = db.query(Candidatura.candidato_id).filter(
                                    Candidatura.vaga_id.in_(vaga_ids)
                                ).distinct().count(),
        candidaturas_ativas   = cands_query.filter(
                                    Candidatura.status.in_(_STATUSES_ATIVOS)
                                ).count(),
        em_triagem            = cands_query.filter(
                                    Candidatura.status == StatusCandidatura.TRIAGEM_PENDENTE
                                ).count(),
        entrevistas_agendadas = db.query(Entrevista).join(
                                    Candidatura, Entrevista.candidatura_id == Candidatura.id
                                ).filter(
                                    Candidatura.vaga_id.in_(vaga_ids),
                                    Entrevista.status == "agendada",
                                ).count(),
        decisoes_pendentes    = cands_query.filter(
                                    Candidatura.status == StatusCandidatura.DECISAO_PENDENTE
                                ).count(),
        contratados_total     = cands_query.filter(
                                    Candidatura.status == StatusCandidatura.CONTRATADO
                                ).count(),
    )


@router.get("/funil", response_model=FunilResponse)
def funil(
    vaga_id : str | None = Query(None),
    db      : Session    = DB,
    usuario              = Depends(get_usuario_atual),
):
    """Distribuição de candidaturas por etapa, filtrada pelas vagas do usuário."""
    vaga_ids = _vagas_ids_query(usuario, db)
    query    = db.query(
        Candidatura.status,
        func.count(Candidatura.id).label("qtd"),
    ).filter(Candidatura.vaga_id.in_(vaga_ids))

    vaga_nome = None
    if vaga_id:
        query = query.filter(Candidatura.vaga_id == vaga_id)
        vaga  = db.query(Vaga).filter(Vaga.id == vaga_id).first()
        vaga_nome = vaga.nome if vaga else None

    query = query.group_by(Candidatura.status)

    # .value porque str(StatusCandidatura.X) → "StatusCandidatura.X", não "x"
    contagens: dict[str, int] = {s.value: q for s, q in query.all()}
    total = sum(contagens.values())

    etapas = [
        EtapaFunil(status=status, label=label, quantidade=contagens.get(status, 0), cor=cor)
        for status, label, cor in _ETAPAS_FUNIL
        if contagens.get(status, 0) > 0
    ]

    return FunilResponse(vaga_id=vaga_id, vaga_nome=vaga_nome, etapas=etapas, total=total)


@router.get("/scores", response_model=DistribuicaoScores)
def distribuicao_scores(
    vaga_id : str     = Query(...),
    db      : Session = DB,
    usuario           = Depends(get_usuario_atual),
):
    """Histograma de scores curriculares para uma vaga."""
    # JOIN evita a conversão implícita de subquery → select que gera warning no SA2
    scores = [
        s for (s,) in db.query(Curriculo.score_curriculo)
            .join(Candidatura, Curriculo.candidatura_id == Candidatura.id)
            .filter(Candidatura.vaga_id == vaga_id)
            .filter(Curriculo.score_curriculo.is_not(None))
            .all()
    ]

    # Faixas com hífen simples para compatibilidade garantida no split do frontend
    buckets_map: dict[str, int] = {f"{i}-{i+10}": 0 for i in range(0, 100, 10)}
    for s in scores:
        idx = min(int(s // 10) * 10, 90)
        buckets_map[f"{idx}-{idx+10}"] += 1

    n       = len(scores)
    media   = round(sum(scores) / n, 1) if n else None
    sorted_ = sorted(scores)
    mediana = (
        round((sorted_[n // 2 - 1] + sorted_[n // 2]) / 2, 1) if n >= 2
        else sorted_[0] if n == 1
        else None
    )

    return DistribuicaoScores(
        vaga_id = vaga_id,
        buckets = [BucketScore(faixa=k, quantidade=v) for k, v in buckets_map.items()],
        media   = media,
        mediana = mediana,
    )
