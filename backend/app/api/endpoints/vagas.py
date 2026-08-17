import csv
import io
from datetime import datetime

from app.ai.market_analyzer import analisar_mercado
from app.ai.matching_engine import calcular_score_curriculo, calcular_score_final
from app.ai.resume_parser import vetorizar_texto
from app.ai.tasks import _recalcular_scores_mercado, atualizar_mercado_vaga
from app.api.deps import DB
from app.core.auth import APENAS_ADMIN, QUALQUER_PAPEL, get_usuario_atual
from app.core.logger import get_logger
from app.models.candidatura import Candidatura
from app.models.curriculo import Curriculo
from app.models.entrevista import Entrevista
from app.models.usuario import PapelUsuario
from app.models.vaga import Vaga
from app.schemas.candidatura import CandidaturaRerankItem
from app.schemas.vaga import (
    RhsAutorizadosUpdate,
    VagaCreate,
    VagaResponse,
    VagaUpdatePesos,
    VagaUpdateRequisitos,
)
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

logger = get_logger("VAGAS")

router = APIRouter()


def _ordenar_vagas(query):
    """Aberta mais recente → aberta mais antiga → pausada → fechada."""
    return query.order_by(
        case(
            (Vaga.status == "aberta",  0),
            (Vaga.status == "pausada", 1),
            (Vaga.status == "fechada", 2),
            else_=3,
        ),
        Vaga.criado_em.desc(),
    )


def _pode_editar_vaga(usuario, vaga) -> bool:
    """
    Admin pode sempre.
    RH pode se a vaga não tiver rhs_autorizados (vagas legadas / criadas por admin)
    ou se estiver na lista.
    """
    if usuario.papel == PapelUsuario.ADMIN:
        return True
    if usuario.papel == PapelUsuario.RH:
        if not vaga.rhs_autorizados:
            return True
        return str(usuario.id) in vaga.rhs_autorizados
    return False


@router.post("/", response_model=VagaResponse, status_code=201)
def criar_vaga(dados: VagaCreate, db: Session = DB, usuario=Depends(get_usuario_atual)):
    if usuario.papel not in (PapelUsuario.RH, PapelUsuario.ADMIN):
        raise HTTPException(status_code=403, detail="Apenas RH ou Admin pode criar vagas")

    payload = dados.model_dump()
    payload["vetor_vaga"]    = vetorizar_texto(dados.requisitos_texto)
    payload["criado_por_id"] = usuario.id
    if usuario.papel == PapelUsuario.RH:
        payload["rhs_autorizados"] = [str(usuario.id)]
    # Admin cria com rhs_autorizados=None → qualquer RH pode editar

    vaga = Vaga(**payload)
    db.add(vaga)
    db.flush()  # garante vaga.id disponível antes do historico

    vaga.historico = [{
        "tipo" : "vaga_criada",
        "ator" : usuario.nome,
        "em"   : datetime.utcnow().isoformat(),
    }]

    db.commit()
    db.refresh(vaga)
    atualizar_mercado_vaga.delay(str(vaga.id))
    return vaga


@router.patch("/{vaga_id}/requisitos", response_model=VagaResponse)
def atualizar_requisitos(
    vaga_id: str,
    dados: VagaUpdateRequisitos,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if not _pode_editar_vaga(usuario, vaga):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta vaga")

    if dados.nome is not None:
        vaga.nome = dados.nome

    if dados.requisitos_texto is not None:
        vaga.requisitos_texto = dados.requisitos_texto
        vaga.vetor_vaga       = vetorizar_texto(dados.requisitos_texto)
        # Requisitos mudaram → recalcula scores e explicações de todos os CVs
        _recalcular_scores_vaga(vaga, db)

    novo_hist = list(vaga.historico or [])
    novo_hist.append({
        "tipo" : "requisitos_alterados",
        "ator" : usuario.nome,
        "em"   : datetime.utcnow().isoformat(),
    })
    vaga.historico = novo_hist

    db.commit()
    db.refresh(vaga)
    return vaga


@router.get("/", response_model=list[VagaResponse])
def listar_vagas(
    db     : Session = DB,
    usuario=Depends(get_usuario_atual),
):
    """
    RH e Admin: todas as vagas ordenadas (aberta-recente > aberta-antiga > pausada > fechada).
    Gestor: somente vagas onde seu UUID está em gestores_ids, mesma ordenação.
    """
    query = db.query(Vaga)
    uid = str(usuario.id)

    if usuario.papel == PapelUsuario.GESTOR:
        query = query.filter(Vaga.gestores_ids.contains([uid]))
    elif usuario.papel == PapelUsuario.RH:
        # Mostra vagas sem restrição (rhs_autorizados SQL NULL) ou onde o RH está autorizado.
        # none_as_null=True garante que Python None → SQL NULL (não JSON null).
        query = query.filter(
            or_(
                Vaga.rhs_autorizados == None,  # noqa: E711
                Vaga.rhs_autorizados.contains([uid]),
            )
        )

    return _ordenar_vagas(query).all()


@router.get("/{vaga_id}", response_model=VagaResponse)
def buscar_vaga(vaga_id: str, db: Session = DB, _=QUALQUER_PAPEL):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return vaga


def _recalcular_scores_vaga(vaga: Vaga, db: Session) -> int:
    from app.ai.feature_extractor import (
        calcular_bonus_estrutural,
        extrair_features_curriculo,
        extrair_features_vaga,
    )
    from app.ai.matching_engine import (
        calcular_score_rh,
        calcular_score_rh_multi_secao,
        gerar_explicacao,
    )

    termos = [t["termo"] for t in (vaga.ranking_mercado or {}).get("termos", [])]
    feat_vaga = extrair_features_vaga(vaga.requisitos_texto or "", termos)

    candidaturas = db.query(Candidatura).filter(Candidatura.vaga_id == vaga.id).all()
    atualizadas = 0
    for cand in candidaturas:
        curriculo = db.query(Curriculo).filter(Curriculo.candidatura_id == cand.id).first()
        if not curriculo or curriculo.score_rh is None:
            continue

        # Recalcula score_rh semântico a partir dos vetores quando disponível
        if curriculo.vetor_embedding is not None and vaga.vetor_vaga is not None:
            s_rh = (
                calcular_score_rh_multi_secao(curriculo.vetor_embedding, vaga.vetor_vaga, curriculo.vetor_secao_exp)
                if curriculo.vetor_secao_exp is not None
                else calcular_score_rh(curriculo.vetor_embedding, vaga.vetor_vaga)
            )
        else:
            s_rh = curriculo.score_rh / 100

        s_mkt  = (curriculo.score_mercado or 0) / 100
        feat_cv = extrair_features_curriculo(curriculo.texto_extraido or "")
        bonus   = calcular_bonus_estrutural(feat_cv, feat_vaga)

        novo_score = calcular_score_curriculo(
            s_rh, s_mkt,
            vaga.peso_rh,
            vaga.peso_mercado,
            bonus,
        )
        curriculo.score_rh        = round(s_rh * 100, 1)
        curriculo.score_mercado   = round(s_mkt * 100, 1)
        curriculo.score_curriculo = novo_score
        curriculo.explicacao = gerar_explicacao(
            s_rh, s_mkt, novo_score,
            vaga.peso_rh, vaga.peso_mercado,
            features_cv=feat_cv, features_vaga=feat_vaga,
            bonus_estrutural=bonus,
        )

        entrevistas = db.query(Entrevista).filter(
            Entrevista.candidatura_id == cand.id,
            Entrevista.status == "realizada",
        ).all()
        score_rh_ent  = next((e.score_manual for e in entrevistas if e.tipo == "rh"),      None)
        score_tec_ent = next((e.score_manual for e in entrevistas if e.tipo == "tecnica"), None)

        cand.score_total = calcular_score_final(
            novo_score, score_rh_ent, score_tec_ent,
            vaga.peso_curriculo, vaga.peso_entrevista_rh, vaga.peso_entrevista_tec,
        )
        atualizadas += 1
    return atualizadas


@router.patch("/{vaga_id}/pesos", response_model=VagaResponse)
def atualizar_pesos(
    vaga_id: str,
    dados: VagaUpdatePesos,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if not _pode_editar_vaga(usuario, vaga):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta vaga")
    pesos_anteriores = {
        "rh": vaga.peso_rh, "mercado": vaga.peso_mercado,
        "curriculo": vaga.peso_curriculo,
        "entrevista_rh": vaga.peso_entrevista_rh, "entrevista_tec": vaga.peso_entrevista_tec,
    }
    vaga.peso_rh             = dados.peso_rh
    vaga.peso_mercado        = dados.peso_mercado
    vaga.peso_curriculo      = dados.peso_curriculo
    vaga.peso_entrevista_rh  = dados.peso_entrevista_rh
    vaga.peso_entrevista_tec = dados.peso_entrevista_tec
    _recalcular_scores_vaga(vaga, db)

    novo_hist = list(vaga.historico or [])
    novo_hist.append({
        "tipo"            : "pesos_alterados",
        "pesos_anteriores": pesos_anteriores,
        "pesos_novos"     : {
            "rh": dados.peso_rh, "mercado": dados.peso_mercado,
            "curriculo": dados.peso_curriculo,
            "entrevista_rh": dados.peso_entrevista_rh, "entrevista_tec": dados.peso_entrevista_tec,
        },
        "ator": usuario.nome,
        "em"  : datetime.utcnow().isoformat(),
    })
    vaga.historico = novo_hist

    db.commit()
    db.refresh(vaga)
    return vaga


@router.patch("/{vaga_id}/status", response_model=VagaResponse)
def atualizar_status(
    vaga_id: str,
    status: str,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    if status not in ("aberta", "pausada", "fechada"):
        raise HTTPException(status_code=400, detail="Status inválido")
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if not _pode_editar_vaga(usuario, vaga):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta vaga")

    status_anterior = vaga.status
    vaga.status = status

    novo_hist = list(vaga.historico or [])
    novo_hist.append({
        "tipo" : "vaga_status",
        "de"   : status_anterior,
        "para" : status,
        "ator" : usuario.nome,
        "em"   : datetime.utcnow().isoformat(),
    })
    vaga.historico = novo_hist

    db.commit()
    db.refresh(vaga)
    return vaga


class GestoresUpdate(BaseModel):
    gestores_ids: list[str]


@router.patch("/{vaga_id}/gestores", response_model=VagaResponse)
def atualizar_gestores(
    vaga_id: str,
    dados: GestoresUpdate,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if not _pode_editar_vaga(usuario, vaga):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta vaga")
    vaga.gestores_ids = dados.gestores_ids
    db.commit()
    db.refresh(vaga)
    return vaga


@router.patch("/{vaga_id}/rhs-autorizados", response_model=VagaResponse)
def atualizar_rhs_autorizados(
    vaga_id: str,
    dados: RhsAutorizadosUpdate,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    """
    Somente o criador da vaga ou Admin pode gerenciar os RHs autorizados.
    O criador é sempre mantido na lista (não pode se auto-remover).
    """
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    eh_criador = str(usuario.id) == str(vaga.criado_por_id)
    if usuario.papel != PapelUsuario.ADMIN and not eh_criador:
        raise HTTPException(status_code=403, detail="Apenas o criador da vaga ou Admin pode gerenciar os RHs autorizados")

    # Garante que o criador sempre permanece na lista
    nova_lista = list(dados.rhs_autorizados)
    if vaga.criado_por_id and str(vaga.criado_por_id) not in nova_lista:
        nova_lista.insert(0, str(vaga.criado_por_id))

    vaga.rhs_autorizados = nova_lista
    db.commit()
    db.refresh(vaga)
    return vaga


@router.delete("/{vaga_id}", response_model=VagaResponse, status_code=200)
def deletar_vaga(vaga_id: str, db: Session = DB, _=APENAS_ADMIN):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.status = "fechada"
    db.commit()
    db.refresh(vaga)
    return vaga


@router.post("/{vaga_id}/rerankar", response_model=list[CandidaturaRerankItem])
def rerankar_candidaturas(
    vaga_id : str,
    db      : Session = DB,
    usuario = Depends(get_usuario_atual),
):
    """
    Reordena os candidatos da vaga usando cross-encoder (mais preciso que bi-encoder).

    Fluxo:
      1. Carrega os top-N candidaturas ordenadas por score_curriculo (bi-encoder)
      2. Aplica o cross-encoder sobre (vaga_requisitos, trecho_cv) de cada uma
      3. Retorna a lista reordenada com score_rerank adicionado

    O cross-encoder é carregado na primeira chamada (~2–5s) e fica em memória.
    Chamadas subsequentes são mais rápidas.
    """
    import time

    from app.ai.reranker import rerankar
    from app.core.config import settings
    from app.models.curriculo import Curriculo

    t_inicio = time.perf_counter()

    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    logger.info("rerankar endpoint: vaga_id=%s, usuário=%s", vaga_id, getattr(usuario, "email", "?"))

    # Carrega candidaturas com curriculo processado, ordenadas por score
    candidaturas = (
        db.query(Candidatura)
        .filter(Candidatura.vaga_id == vaga_id)
        .all()
    )

    logger.info("rerankar endpoint: %d candidatura(s) carregada(s) para a vaga.", len(candidaturas))

    top_n   = settings.RERANKER_TOP_N
    cur_map = {
        str(c.candidatura_id): c
        for c in db.query(Curriculo)
            .filter(Curriculo.candidatura_id.in_([str(ca.id) for ca in candidaturas]))
            .all()
    }

    logger.debug("rerankar endpoint: %d currículo(s) encontrado(s). top_n=%s", len(cur_map), top_n)

    # Prepara lista para o reranker
    items = []
    sem_curriculo = 0
    for ca in candidaturas:
        cur = cur_map.get(str(ca.id))
        if cur is None:
            sem_curriculo += 1
        items.append({
            "id"               : str(ca.id),
            "candidatura"      : ca,
            "curriculo"        : cur,
            "texto_curriculo"  : (cur.texto_extraido or "") if cur else "",
            "score_curriculo"  : (cur.score_curriculo or 0) if cur else 0,
        })

    if sem_curriculo:
        logger.warning(
            "rerankar endpoint: %d candidatura(s) sem currículo processado (serão enviadas com texto vazio).",
            sem_curriculo,
        )

    # Ordena por score bi-encoder e pega top-N
    items_sorted = sorted(items, key=lambda x: x["score_curriculo"], reverse=True)

    reranked = rerankar(
        texto_vaga   = vaga.requisitos_texto,
        candidaturas = items_sorted,
        top_n        = top_n,
    )

    resultado = []
    for item in reranked:
        ca  = item["candidatura"]
        cur = item["curriculo"]
        resultado.append(CandidaturaRerankItem(
            id              = ca.id,
            candidato_id    = ca.candidato_id,
            vaga_id         = ca.vaga_id,
            status          = ca.status,
            score_total     = ca.score_total,
            score_curriculo = (cur.score_curriculo if cur else None),
            score_rerank    = item.get("score_rerank"),
            candidato       = ca.candidato,
            curriculo       = cur,
        ))

    logger.info(
        "rerankar endpoint: concluído em %.2fs — %d item(ns) retornado(s).",
        time.perf_counter() - t_inicio, len(resultado),
    )

    return resultado


@router.post("/{vaga_id}/analisar-mercado", response_model=VagaResponse)
async def analisar_mercado_vaga(
    vaga_id: str,
    db: Session = DB,
    usuario=Depends(get_usuario_atual),
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if not _pode_editar_vaga(usuario, vaga):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta vaga")
    resultado = await analisar_mercado(vaga.nome)
    vaga.vetor_mercado   = resultado["vetor_mercado"]
    vaga.ranking_mercado = {
        "termos"                : resultado["termos_frequentes"],
        "total_vagas_analisadas": resultado["total_vagas_analisadas"],
        "fonte"                 : resultado["fonte"],
        "atualizado_em"         : __import__("datetime").datetime.utcnow().isoformat(),
    }
    db.commit()
    logger.info(
        f"vaga={vaga_id} nome='{vaga.nome}' | mercado atualizado | "
        f"{resultado['total_vagas_analisadas']} vagas analisadas | fonte={resultado['fonte']}"
    )

    # Recalcula scores de mercado dos CVs já processados com o novo vetor
    recalculados = _recalcular_scores_mercado(db, vaga)
    if recalculados:
        logger.info(f"vaga={vaga_id} | {recalculados} CVs recalculados com novo vetor de mercado")
    else:
        logger.info(f"vaga={vaga_id} | nenhum CV processado para recalcular")

    db.refresh(vaga)
    return vaga


@router.get("/{vaga_id}/exportar")
def exportar_candidatos(
    vaga_id: str,
    db: Session = DB,
    _=QUALQUER_PAPEL,
):
    """Exporta candidatos da vaga como CSV com scores e skills."""
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    candidaturas = (
        db.query(Candidatura)
        .filter(Candidatura.vaga_id == vaga_id)
        .order_by(
            Candidatura.score_total.desc().nullslast(),
        )
        .all()
    )

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow([
        "Nome", "E-mail", "Telefone", "Cidade", "Estado",
        "Status", "Score currículo", "Score RH", "Score mercado",
        "Score total", "Anos experiência", "Skills em comum",
    ])

    STATUS_PT = {
        "novo": "Novo", "triagem_pendente": "Triagem pendente",
        "aprovado_triagem": "Aprovado triagem", "reprovado_triagem": "Reprovado triagem",
        "entrevista_rh_agendada": "Entrevista RH agendada",
        "entrevista_rh_realizada": "Entrevista RH realizada",
        "reprovado_rh": "Reprovado RH",
        "entrevista_tec_agendada": "Entrevista técnica agendada",
        "entrevista_tec_realizada": "Entrevista técnica realizada",
        "reprovado_tecnico": "Reprovado técnico",
        "decisao_pendente": "Decisão pendente",
        "contratado": "Contratado", "nao_aprovado": "Não aprovado",
        "banco_de_talentos": "Banco de talentos",
    }

    def _csv_str(value) -> str:
        """Evita CSV formula injection prefixando valores que iniciam com =+-@"""
        s = str(value) if value is not None else ""
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + s
        return s

    for cand in candidaturas:
        c   = cand.candidato
        cur = cand.curriculo
        expl = cur.explicacao if cur else None
        sinais = (expl or {}).get("sinais_estruturais", {})
        skills = ", ".join(sinais.get("habilidades_em_comum", []))
        anos   = sinais.get("anos_experiencia", "")
        status_val = str(cand.status.value if hasattr(cand.status, "value") else cand.status)
        w.writerow([
            _csv_str(c.nome if c else ""),
            _csv_str(c.email if c else ""),
            _csv_str(c.telefone or "" if c else ""),
            _csv_str(c.cidade or "" if c else ""),
            _csv_str(c.estado or "" if c else ""),
            STATUS_PT.get(status_val, status_val),
            cur.score_curriculo if cur else "",
            cur.score_rh        if cur else "",
            cur.score_mercado   if cur else "",
            cand.score_total or "",
            anos,
            _csv_str(skills),
        ])

    buf.seek(0)
    import re as _re
    nome_arquivo = _re.sub(r'[^\w\-]', '_', vaga.nome.lower())[:40]
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}_candidatos.csv"'},
    )
