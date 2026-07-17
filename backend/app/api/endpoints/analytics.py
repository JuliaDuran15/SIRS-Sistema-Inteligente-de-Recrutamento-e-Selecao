"""
Endpoints de analytics — funil, scores, resumo.
Dados filtrados pelas vagas visíveis ao usuário logado:
  Admin  → todos
  RH     → vagas onde é criador ou está em rhs_autorizados
  Gestor → vagas onde está em gestores_ids
"""
from app.api.deps import DB
from app.core.auth import get_usuario_atual
from app.models.candidato import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.entrevista import Entrevista
from app.models.usuario import PapelUsuario, Usuario
from app.models.vaga import Vaga
from fastapi import APIRouter, Depends, HTTPException, Query
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


class VagaScore(BaseModel):
    vaga_id          : str
    vaga_nome        : str
    score_medio      : float
    total_candidatos : int


class ScoresPorVaga(BaseModel):
    vagas : list[VagaScore]


class SkillCount(BaseModel):
    skill    : str
    contagem : int


class TopSkills(BaseModel):
    skills    : list[SkillCount]
    vaga_id   : str | None
    vaga_nome : str | None


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
                Vaga.rhs_autorizados == None,  # noqa: E711
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
    if n == 0:
        mediana = None
    elif n % 2 == 1:
        mediana = round(sorted_[n // 2], 1)
    else:
        mediana = round((sorted_[n // 2 - 1] + sorted_[n // 2]) / 2, 1)

    return DistribuicaoScores(
        vaga_id = vaga_id,
        buckets = [BucketScore(faixa=k, quantidade=v) for k, v in buckets_map.items()],
        media   = media,
        mediana = mediana,
    )


@router.get("/scores-por-vaga", response_model=ScoresPorVaga)
def scores_por_vaga(
    db      : Session = DB,
    usuario           = Depends(get_usuario_atual),
):
    """Score médio de currículo agrupado por vaga (top 10 com mais candidatos)."""
    vaga_ids = _vagas_ids_query(usuario, db)
    rows = (
        db.query(
            Vaga.id,
            Vaga.nome,
            func.avg(Curriculo.score_curriculo).label("media"),
            func.count(Curriculo.id).label("total"),
        )
        .join(Candidatura, Candidatura.vaga_id == Vaga.id)
        .join(Curriculo,   Curriculo.candidatura_id == Candidatura.id)
        .filter(Vaga.id.in_(vaga_ids))
        .filter(Curriculo.score_curriculo.is_not(None))
        .group_by(Vaga.id, Vaga.nome)
        .order_by(func.count(Curriculo.id).desc())
        .limit(10)
        .all()
    )
    return ScoresPorVaga(vagas=[
        VagaScore(
            vaga_id=str(r.id),
            vaga_nome=r.nome,
            score_medio=round(float(r.media), 1),
            total_candidatos=r.total,
        )
        for r in rows
    ])


@router.get("/top-skills", response_model=TopSkills)
def top_skills(
    vaga_id : str | None = Query(None),
    db      : Session    = DB,
    usuario              = Depends(get_usuario_atual),
):
    """Skills mais frequentes extraídas dos currículos (top 15)."""
    vaga_ids = _vagas_ids_query(usuario, db)
    query = (
        db.query(Curriculo.explicacao)
        .join(Candidatura, Curriculo.candidatura_id == Candidatura.id)
        .filter(Candidatura.vaga_id.in_(vaga_ids))
        .filter(Curriculo.explicacao.is_not(None))
    )
    if vaga_id:
        query = query.filter(Candidatura.vaga_id == vaga_id)

    contagem: dict[str, int] = {}
    for (exp,) in query.all():
        skills = (exp or {}).get("sinais_estruturais", {}).get("habilidades_em_comum", [])
        for s in skills:
            s = s.strip().lower()
            if s:
                contagem[s] = contagem.get(s, 0) + 1

    top = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:15]

    vaga_nome = None
    if vaga_id:
        v = db.query(Vaga.nome).filter(Vaga.id == vaga_id).scalar()
        vaga_nome = v

    return TopSkills(
        skills=[SkillCount(skill=s, contagem=c) for s, c in top],
        vaga_id=vaga_id,
        vaga_nome=vaga_nome,
    )


# ── Auditoria ─────────────────────────────────────────────────────────────────

class EventoAuditoria(BaseModel):
    tipo            : str | None = None
    candidatura_id  : str | None = None
    candidato_id    : str | None = None
    candidato_nome  : str | None = None
    candidato_email : str | None = None
    vaga_nome       : str | None = None
    de              : str | None = None
    para            : str | None = None
    ator            : str | None = None
    em              : str | None = None
    extra           : dict | None = None


class AuditoriaResponse(BaseModel):
    eventos : list[EventoAuditoria]
    total   : int
    limit   : int
    offset  : int


@router.get("/auditoria", response_model=AuditoriaResponse)
def auditoria(
    limit   : int           = Query(50, ge=1, le=200),
    offset  : int           = Query(0,  ge=0),
    vaga_id : str | None    = Query(None),
    ator    : str | None    = Query(None, description="Filtra por nome do ator (parcial)"),
    para    : str | None    = Query(None, description="Filtra pelo status de destino (transições)"),
    tipo    : str | None    = Query(None, description="Filtra por tipo de evento especial"),
    db      : Session       = DB,
    usuario = Depends(get_usuario_atual),
):
    """Retorna o log de transições de candidaturas e alterações de candidatos. Apenas Admin."""
    if usuario.papel != PapelUsuario.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem acessar a auditoria")

    eventos: list[dict] = []

    # Quando tipo especial está ativo, ignorar fontes que não produzem esse tipo
    _apenas_status   = tipo is None and para is not None
    _apenas_especial = tipo is not None

    # ── Eventos de candidatura (transições de status) ─────────────────────────
    _TIPOS_CANDIDATURA = {"triagem_lote", "resultado_entrevista"}
    _incluir_cand = not _apenas_especial or tipo in _TIPOS_CANDIDATURA or not tipo

    if not _apenas_especial or tipo in _TIPOS_CANDIDATURA:
        query_cand = (
            db.query(Candidatura, Candidato, Vaga)
            .join(Candidato, Candidatura.candidato_id == Candidato.id)
            .join(Vaga,      Candidatura.vaga_id      == Vaga.id)
        )
        if vaga_id:
            query_cand = query_cand.filter(Candidatura.vaga_id == vaga_id)
    else:
        query_cand = []

    for cand, candidato, vaga in query_cand:
        for evt in (cand.historico or []):
            evt_ator = evt.get("ator") or ""
            evt_para = evt.get("para") or ""
            evt_tipo = evt.get("tipo")

            # Pular tipos especiais neste bloco (tratados abaixo)
            if evt_tipo in {"triagem_lote", "resultado_entrevista", "resubmissao_duplicata"}:
                continue
            if ator and ator.lower() not in evt_ator.lower():
                continue
            if para and para != evt_para:
                continue
            if tipo:  # quando tipo especial ativo, pular transições puras
                continue
            eventos.append({
                "tipo"           : None,
                "candidatura_id" : str(cand.id),
                "candidato_id"   : str(candidato.id),
                "candidato_nome" : candidato.nome,
                "candidato_email": candidato.email,
                "vaga_nome"      : vaga.nome,
                "de"             : evt.get("de"),
                "para"           : evt_para or None,
                "ator"           : evt_ator or None,
                "em"             : evt.get("em"),
            })

    # ── Eventos de candidato (alterações de e-mail) — apenas sem filtro de vaga
    if not vaga_id and not para and (not tipo or tipo == "alteracao_email"):
        for candidato in db.query(Candidato).all():
            for evt in (candidato.historico or []):
                if evt.get("tipo") != "alteracao_email":
                    continue
                evt_ator = evt.get("ator") or ""
                if ator and ator.lower() not in evt_ator.lower():
                    continue
                eventos.append({
                    "tipo"           : "alteracao_email",
                    "candidatura_id" : None,
                    "candidato_id"   : str(candidato.id),
                    "candidato_nome" : candidato.nome,
                    "candidato_email": candidato.email,
                    "vaga_nome"      : None,
                    "de"             : evt.get("email_anterior"),
                    "para"           : evt.get("email_novo"),
                    "ator"           : evt_ator or None,
                    "em"             : evt.get("em"),
                })

    # ── Eventos de vaga (criação, status, pesos, requisitos, exclusão de candidatura)
    _TIPOS_VAGA = {"vaga_criada", "vaga_status", "pesos_alterados",
                   "requisitos_alterados", "candidatura_excluida"}

    query_vagas = db.query(Vaga)
    if vaga_id:
        query_vagas = query_vagas.filter(Vaga.id == vaga_id)

    for vaga in query_vagas.all():
        for evt in (vaga.historico or []):
            tipo_evt = evt.get("tipo")
            if tipo_evt not in _TIPOS_VAGA:
                continue
            if para:
                continue
            if tipo and tipo != tipo_evt:
                continue
            evt_ator = evt.get("ator") or ""
            if ator and ator.lower() not in evt_ator.lower():
                continue

            if tipo_evt == "candidatura_excluida":
                eventos.append({
                    "tipo"           : "candidatura_excluida",
                    "candidatura_id" : evt.get("candidatura_id"),
                    "candidato_id"   : None,
                    "candidato_nome" : evt.get("candidato_nome"),
                    "candidato_email": evt.get("candidato_email"),
                    "vaga_nome"      : vaga.nome,
                    "de"             : evt.get("status_era"),
                    "para"           : None,
                    "ator"           : evt_ator or None,
                    "em"             : evt.get("em"),
                })
            elif tipo_evt == "pesos_alterados":
                def _fmt_pesos(p: dict) -> str:
                    return (f"CV {int(p.get('curriculo',0)*100)}% · "
                            f"RH {int(p.get('rh',0)*100)}% · "
                            f"Mercado {int(p.get('mercado',0)*100)}% · "
                            f"Entrev.RH {int(p.get('entrevista_rh',0)*100)}% · "
                            f"Entrev.Téc {int(p.get('entrevista_tec',0)*100)}%")
                eventos.append({
                    "tipo"           : "pesos_alterados",
                    "candidatura_id" : None,
                    "candidato_id"   : None,
                    "candidato_nome" : None,
                    "candidato_email": None,
                    "vaga_nome"      : vaga.nome,
                    "de"             : _fmt_pesos(evt.get("pesos_anteriores") or {}),
                    "para"           : _fmt_pesos(evt.get("pesos_novos") or {}),
                    "ator"           : evt_ator or None,
                    "em"             : evt.get("em"),
                })
            else:
                eventos.append({
                    "tipo"           : tipo_evt,
                    "candidatura_id" : None,
                    "candidato_id"   : None,
                    "candidato_nome" : None,
                    "candidato_email": None,
                    "vaga_nome"      : vaga.nome,
                    "de"             : evt.get("de"),
                    "para"           : evt.get("para"),
                    "ator"           : evt_ator or None,
                    "em"             : evt.get("em"),
                })

    # ── Eventos de triagem em lote (marcadores nos historicos de candidatura)
    if (not para or para == "triagem_lote") and (not tipo or tipo == "triagem_lote"):
        for cand, candidato, vaga in (
            db.query(Candidatura, Candidato, Vaga)
            .join(Candidato, Candidatura.candidato_id == Candidato.id)
            .join(Vaga,      Candidatura.vaga_id      == Vaga.id)
            .filter(Candidatura.vaga_id == vaga_id if vaga_id else True)
            .all()
        ):
            for evt in (cand.historico or []):
                if evt.get("tipo") != "triagem_lote":
                    continue
                evt_ator = evt.get("ator") or ""
                if ator and ator.lower() not in evt_ator.lower():
                    continue
                eventos.append({
                    "tipo"           : "triagem_lote",
                    "candidatura_id" : str(cand.id),
                    "candidato_id"   : str(candidato.id),
                    "candidato_nome" : candidato.nome,
                    "candidato_email": candidato.email,
                    "vaga_nome"      : vaga.nome,
                    "de"             : None,
                    "para"           : evt.get("lote_id"),
                    "ator"           : evt_ator or None,
                    "em"             : evt.get("em"),
                    "extra"          : {"total": evt.get("total")},
                })

    # ── Resultado de entrevista
    if not tipo or tipo == "resultado_entrevista":
      for cand, candidato, vaga in (
        db.query(Candidatura, Candidato, Vaga)
        .join(Candidato, Candidatura.candidato_id == Candidato.id)
        .join(Vaga,      Candidatura.vaga_id      == Vaga.id)
        .filter(Candidatura.vaga_id == vaga_id if vaga_id else True)
        .all()
      ):
        for evt in (cand.historico or []):
            if evt.get("tipo") != "resultado_entrevista":
                continue
            if para:
                continue
            evt_ator = evt.get("ator") or ""
            if ator and ator.lower() not in evt_ator.lower():
                continue
            eventos.append({
                "tipo"           : "resultado_entrevista",
                "candidatura_id" : str(cand.id),
                "candidato_id"   : str(candidato.id),
                "candidato_nome" : candidato.nome,
                "candidato_email": candidato.email,
                "vaga_nome"      : vaga.nome,
                "de"             : evt.get("tipo_entrevista"),
                "para"           : str(evt.get("score", "")),
                "ator"           : evt_ator or None,
                "em"             : evt.get("em"),
                "extra"          : {"reedicao": evt.get("reedicao", False)},
            })

    # ── Eventos de login (sucesso, falha, fora de horário)
    if not vaga_id and not para and (not tipo or tipo == "login"):
        for usr in db.query(Usuario).all():
            for evt in (usr.historico or []):
                if evt.get("tipo") != "login":
                    continue
                evt_ator = usr.nome
                if ator and ator.lower() not in evt_ator.lower():
                    continue
                eventos.append({
                    "tipo"           : "login",
                    "candidatura_id" : None,
                    "candidato_id"   : None,
                    "candidato_nome" : usr.nome,
                    "candidato_email": usr.email,
                    "vaga_nome"      : None,
                    "de"             : None,
                    "para"           : None,
                    "ator"           : usr.nome,
                    "em"             : evt.get("em"),
                    "extra"          : {
                        "sucesso"     : evt.get("sucesso", True),
                        "motivo"      : evt.get("motivo"),
                        "fora_horario": evt.get("fora_horario", False),
                        "ip"          : evt.get("ip"),
                        "papel"       : usr.papel.value,
                    },
                })

    eventos.sort(key=lambda e: e["em"] or "", reverse=True)
    total  = len(eventos)
    pagina = eventos[offset : offset + limit]

    return AuditoriaResponse(
        eventos=[EventoAuditoria(**e) for e in pagina],
        total=total,
        limit=limit,
        offset=offset,
    )
