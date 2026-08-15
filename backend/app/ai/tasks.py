import asyncio
import unicodedata
from datetime import datetime

import app.db.base  # noqa: F401 — garante que todos os models estão mapeados
from app.ai.feature_extractor import (
    calcular_bonus_estrutural,
    extrair_features_curriculo,
    extrair_features_vaga,
)
from app.ai.market_analyzer import analisar_mercado
from app.ai.matching_engine import (
    calcular_score_curriculo,
    calcular_score_final,
    calcular_score_mercado,
    calcular_score_rh,
    calcular_score_rh_multi_secao,
    gerar_explicacao,
)
from app.ai.resume_parser import parsear_curriculo, vetorizar_secoes, vetorizar_texto
from app.core.celery_app import celery_app
from app.core.email import email_cv_processado
from app.core.logger import get_logger
from app.db.session import SessionLocal
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.usuario import Usuario
from app.models.vaga import Vaga

logger = get_logger("TASKS")

_PARTICULAS = {"de", "da", "do", "dos", "das", "e", "a", "o"}


def _normalizar_nome(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _verificar_nome_cv(nome_candidato: str, texto_cv: str) -> dict:
    """
    Verifica se o nome cadastrado aparece nos primeiros 300 chars do CV
    (onde o nome quase sempre está). Retorna um dict com o resultado para
    salvar na explicacao e logar no historico.
    """
    if not nome_candidato or not texto_cv:
        return {"match": True, "confianca": 1.0}

    trecho = texto_cv[:300]
    trecho_norm = _normalizar_nome(trecho)

    tokens = [
        t for t in _normalizar_nome(nome_candidato).split()
        if t not in _PARTICULAS and len(t) > 2
    ]
    if not tokens:
        return {"match": True, "confianca": 1.0}

    encontrados = [t for t in tokens if t in trecho_norm]
    ausentes    = [t for t in tokens if t not in trecho_norm]
    confianca   = round(len(encontrados) / len(tokens), 2)

    return {
        "match"            : confianca >= 0.5,
        "confianca"        : confianca,
        "nome_cadastrado"  : nome_candidato,
        "tokens_ausentes"  : ausentes,
        "trecho_analisado" : trecho.strip()[:120],
    }


def _transicionar(candidatura, novo_status, ator: str = "sistema") -> None:
    """Aplica transição de estado registrando no histórico (sem HTTPException)."""
    from app.api.endpoints.candidaturas import TRANSICOES
    permitidos = TRANSICOES.get(candidatura.status, [])
    if novo_status not in permitidos:
        raise ValueError(
            f"Transição inválida: {candidatura.status.value} → {novo_status.value}"
        )
    historico = list(candidatura.historico or [])
    historico.append({
        "de"  : candidatura.status.value,
        "para": novo_status.value,
        "ator": ator,
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status    = novo_status


def _recalcular_scores_mercado(db, vaga: Vaga) -> int:
    """
    Recalcula score_mercado e score_curriculo para todos os CVs processados
    de uma vaga, usando o vetor_mercado atual.
    Retorna a quantidade de currículos atualizados.
    """
    from app.models.candidatura import Candidatura as _Cand

    novo_vetor = vaga.vetor_mercado
    if novo_vetor is None:
        return 0

    termos = [t["termo"] for t in (vaga.ranking_mercado or {}).get("termos", [])]

    curriculos = (
        db.query(Curriculo)
        .join(_Cand, Curriculo.candidatura_id == _Cand.id)
        .filter(
            _Cand.vaga_id == vaga.id,
            Curriculo.vetor_embedding.isnot(None),
            Curriculo.score_rh.isnot(None),
        )
        .all()
    )

    count = 0
    for cur in curriculos:
        try:
            # Recalcula score_rh semântico puro a partir dos vetores
            if cur.vetor_secao_exp is not None:
                s_rh_raw = calcular_score_rh_multi_secao(
                    cur.vetor_embedding, vaga.vetor_vaga, cur.vetor_secao_exp
                )
            else:
                s_rh_raw = calcular_score_rh(cur.vetor_embedding, vaga.vetor_vaga)

            novo_mkt = calcular_score_mercado(
                cur.vetor_embedding, novo_vetor, vetor_secao_skills=cur.vetor_secao_skills
            )

            feat_cv   = extrair_features_curriculo(cur.texto_extraido or "")
            feat_vaga = extrair_features_vaga(vaga.requisitos_texto, termos)
            bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga)

            novo_final = calcular_score_curriculo(s_rh_raw, novo_mkt, vaga.peso_rh, vaga.peso_mercado, bonus)

            nova_expl = gerar_explicacao(
                s_rh_raw, novo_mkt, novo_final,
                vaga.peso_rh, vaga.peso_mercado,
                features_cv=feat_cv, features_vaga=feat_vaga,
            )

            cur.score_rh        = round(s_rh_raw * 100, 1)
            cur.score_mercado   = round(novo_mkt * 100, 1)
            cur.score_curriculo = novo_final
            cur.explicacao      = nova_expl
            cand = db.query(_Cand).filter(_Cand.id == cur.candidatura_id).first()
            if cand:
                cand.score_total = calcular_score_final(
                    novo_final,
                    cand.score_entrevista_rh,
                    cand.score_entrevista_tec,
                    vaga.peso_curriculo,
                    vaga.peso_entrevista_rh,
                    vaga.peso_entrevista_tec,
                )
            count += 1
        except Exception as exc:
            logger.warning(f"curriculo {cur.id} | falha no recálculo de scores: {exc}")

    if count:
        db.commit()
    return count


def _notificar_rh(db, vaga: Vaga, candidatura: Candidatura, score: float, explicacao: dict | None) -> None:
    """Envia e-mail ao RH criador da vaga informando que o CV foi processado."""
    if not vaga.criado_por_id:
        return
    try:
        rh = db.query(Usuario).filter(Usuario.id == vaga.criado_por_id).first()
        if rh and rh.email:
            enviado = email_cv_processado(
                destinatario   = rh.email,
                nome_rh        = rh.nome,
                candidato_nome = candidatura.candidato.nome if candidatura.candidato else "Candidato",
                vaga_nome      = vaga.nome,
                score          = score,
                explicacao     = explicacao,
            )
            if enviado:
                logger.info(f"e-mail enviado para {rh.email} | score={score}")
    except Exception as exc:
        logger.warning(f"falha ao enviar e-mail de notificação: {exc}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def processar_curriculo(self, candidatura_id: str, caminho_pdf: str):
    logger.info(f"candidatura={candidatura_id} | iniciando processamento de PDF")
    db = SessionLocal()

    try:
        # 1. Busca candidatura e vaga
        candidatura = db.query(Candidatura).filter(
            Candidatura.id == candidatura_id
        ).first()

        if not candidatura:
            raise ValueError(f"Candidatura {candidatura_id} não encontrada")

        vaga = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()

        if not vaga:
            raise ValueError(f"Vaga não encontrada para candidatura {candidatura_id}")

        if vaga.vetor_vaga is None:
            raise ValueError("Vaga não possui vetor — crie a vaga antes de processar currículos")

        # Transição: AGUARDANDO_PROC → PROCESSANDO (retry-safe)
        if candidatura.status == StatusCandidatura.AGUARDANDO_PROC:
            _transicionar(candidatura, StatusCandidatura.PROCESSANDO)
            db.commit()

        # 2. Parseia o currículo — extrai texto e gera vetor
        resultado = parsear_curriculo(caminho_pdf)

        # 3. Vetores de seção (experiência e habilidades)
        vetor_exp    = resultado.get("vetor_secao_exp")
        vetor_skills = resultado.get("vetor_secao_skills")

        # 4. Features estruturais e bônus (calculados antes dos scores)
        termos        = (vaga.ranking_mercado or {}).get("termos")
        if vaga.vetor_mercado is not None:
            vetor_mercado = vaga.vetor_mercado
        else:
            logger.warning(
                f"vaga={vaga.id} | vetor_mercado ausente — score_mercado usará vetor_vaga como fallback"
            )
            vetor_mercado = vaga.vetor_vaga

        feat_cv   = extrair_features_curriculo(resultado["texto_extraido"])
        feat_vaga = extrair_features_vaga(vaga.requisitos_texto, termos)
        bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga)

        # 5. Scores semânticos puros + score final com bônus aplicado ao combinado
        score_rh = calcular_score_rh_multi_secao(
            vetor_embedding = resultado["vetor_embedding"],
            vetor_vaga      = vaga.vetor_vaga,
            vetor_secao_exp = vetor_exp,
        )
        score_mercado = calcular_score_mercado(
            resultado["vetor_embedding"], vetor_mercado, vetor_secao_skills=vetor_skills
        )
        score_curriculo = calcular_score_curriculo(
            score_rh, score_mercado, vaga.peso_rh, vaga.peso_mercado, bonus
        )

        # 6. Explicação XAI
        explicacao = gerar_explicacao(
            score_rh, score_mercado, score_curriculo,
            vaga.peso_rh, vaga.peso_mercado,
            features_cv   = feat_cv,
            features_vaga = feat_vaga,
        )

        # 7. Verificação de nome (aviso suave — não bloqueia)
        nome_candidato = candidatura.candidato.nome if candidatura.candidato else ""
        verif_nome = _verificar_nome_cv(nome_candidato, resultado["texto_extraido"])
        if not verif_nome["match"]:
            logger.warning(
                f"candidatura={candidatura_id} | nome no CV pode divergir do cadastro | "
                f"cadastrado='{verif_nome['nome_cadastrado']}' "
                f"confianca={verif_nome['confianca']} "
                f"ausentes={verif_nome['tokens_ausentes']}"
            )
            hist = list(candidatura.historico or [])
            hist.append({
                "de"    : candidatura.status.value,
                "para"  : candidatura.status.value,
                "ator"  : "sistema",
                "em"    : datetime.utcnow().isoformat(),
                "alerta": "nome_cv_divergente",
                "detalhe": (
                    f"Nome cadastrado '{verif_nome['nome_cadastrado']}' não foi encontrado "
                    f"no início do CV. Tokens ausentes: {', '.join(verif_nome['tokens_ausentes'])}. "
                    f"Verifique se o CV pertence a este candidato."
                ),
            })
            candidatura.historico = hist
        explicacao["alerta_nome"] = verif_nome

        # 8. Salva no banco
        curriculo = db.query(Curriculo).filter(
            Curriculo.candidatura_id == candidatura_id
        ).first()

        if not curriculo:
            curriculo = Curriculo(candidatura_id=candidatura_id)
            db.add(curriculo)

        curriculo.texto_extraido      = resultado["texto_extraido"]
        curriculo.vetor_embedding     = resultado["vetor_embedding"]
        curriculo.vetor_secao_exp     = resultado.get("vetor_secao_exp")
        curriculo.vetor_secao_skills  = resultado.get("vetor_secao_skills")
        curriculo.score_rh        = round(score_rh * 100, 1)
        curriculo.score_mercado   = round(score_mercado * 100, 1)
        curriculo.score_curriculo = score_curriculo
        curriculo.explicacao      = explicacao
        curriculo.processado_em   = datetime.utcnow()

        if candidatura.status == StatusCandidatura.PROCESSANDO:
            _transicionar(candidatura, StatusCandidatura.TRIAGEM_PENDENTE)
        candidatura.score_total = calcular_score_final(
            score_curriculo,
            candidatura.score_entrevista_rh,
            candidatura.score_entrevista_tec,
            vaga.peso_curriculo,
            vaga.peso_entrevista_rh,
            vaga.peso_entrevista_tec,
        )

        db.commit()
        logger.info(
            f"candidatura={candidatura_id} | vaga='{vaga.nome}' | "
            f"score_rh={round(score_rh*100,1)} score_mercado={round(score_mercado*100,1)} "
            f"score_curriculo={score_curriculo}"
        )

        _notificar_rh(db, vaga, candidatura, score_curriculo, explicacao)

        return {
            "status"        : "ok",
            "candidatura_id": candidatura_id,
            "score_curriculo": score_curriculo,
        }

    except ValueError as exc:
        logger.error(f"candidatura={candidatura_id} | ERRO irrecuperável (sem retry): {exc}")
        db.rollback()
        try:
            cand = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
            if cand:
                hist = list(cand.historico or [])
                hist.append({
                    "de"  : cand.status.value,
                    "para": StatusCandidatura.NOVO.value,
                    "ator": "sistema",
                    "em"  : datetime.utcnow().isoformat(),
                    "erro": str(exc),
                })
                cand.historico = hist
                cand.status    = StatusCandidatura.NOVO
                db.commit()
        except Exception:
            db.rollback()

    except Exception as exc:
        logger.error(f"candidatura={candidatura_id} | ERRO no processamento de PDF: {exc}", exc_info=True)
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def atualizar_mercado_vaga(self, vaga_id: str):
    """
    Busca dados de mercado para a vaga e atualiza vetor_mercado.
    Chamada automaticamente quando uma vaga é criada.
    Pode ser chamada manualmente via POST /vagas/{id}/analisar-mercado.
    """
    db = SessionLocal()

    try:
        from app.models.vaga import Vaga
        vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()

        if not vaga:
            raise ValueError(f"Vaga {vaga_id} não encontrada")

        logger.info(f"vaga={vaga_id} nome='{vaga.nome}' | analisando mercado")
        resultado = asyncio.run(analisar_mercado(vaga.nome))

        vaga.vetor_mercado = resultado["vetor_mercado"]
        vaga.ranking_mercado = {
            "termos"                : resultado["termos_frequentes"],
            "total_vagas_analisadas": resultado["total_vagas_analisadas"],
            "fonte"                 : resultado["fonte"],
            "atualizado_em"         : datetime.utcnow().isoformat(),
        }

        db.commit()
        logger.info(
            f"vaga={vaga_id} nome='{vaga.nome}' | mercado atualizado | "
            f"{resultado['total_vagas_analisadas']} vagas analisadas | "
            f"fonte={resultado['fonte']}"
        )

        # Recalcula score_mercado de todos os CVs já processados desta vaga
        atualizados = _recalcular_scores_mercado(db, vaga)
        if atualizados:
            logger.info(f"vaga={vaga_id} | {atualizados} CVs recalculados com novo vetor de mercado")

        return {
            "status"    : "ok",
            "vaga_id"   : vaga_id,
            "termos"    : len(resultado["termos_frequentes"]),
            "cvs_recalc": atualizados,
        }

    except Exception as exc:
        logger.error(f"vaga={vaga_id} | ERRO ao analisar mercado: {exc}", exc_info=True)
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def processar_curriculo_texto(self, candidatura_id: str, texto: str):
    """
    Processa currículo recebido como texto puro (via webhook).
    Equivalente a processar_curriculo, mas sem extração de PDF.
    """
    logger.info(f"candidatura={candidatura_id} | iniciando processamento de texto ({len(texto)} chars)")
    db = SessionLocal()

    try:
        candidatura = db.query(Candidatura).filter(
            Candidatura.id == candidatura_id
        ).first()
        if not candidatura:
            raise ValueError(f"Candidatura {candidatura_id} não encontrada")

        vaga = db.query(Vaga).filter(Vaga.id == candidatura.vaga_id).first()
        if not vaga:
            raise ValueError(f"Vaga não encontrada para candidatura {candidatura_id}")
        if vaga.vetor_vaga is None:
            raise ValueError("Vaga não possui vetor — tente novamente após a vaga ser vetorizada")

        # Transição: AGUARDANDO_PROC → PROCESSANDO (retry-safe)
        if candidatura.status == StatusCandidatura.AGUARDANDO_PROC:
            _transicionar(candidatura, StatusCandidatura.PROCESSANDO)
            db.commit()

        vetor  = vetorizar_texto(texto)
        secs   = vetorizar_secoes(texto)
        termos = (vaga.ranking_mercado or {}).get("termos")

        feat_cv   = extrair_features_curriculo(texto)
        feat_vaga = extrair_features_vaga(vaga.requisitos_texto, termos)
        bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga)

        if vaga.vetor_mercado is not None:
            vetor_mercado = vaga.vetor_mercado
        else:
            logger.warning(
                f"vaga={vaga.id} | vetor_mercado ausente — score_mercado usará vetor_vaga como fallback"
            )
            vetor_mercado = vaga.vetor_vaga
        score_rh = calcular_score_rh_multi_secao(
            vetor_embedding = vetor,
            vetor_vaga      = vaga.vetor_vaga,
            vetor_secao_exp = secs["exp"],
        )
        score_mercado = calcular_score_mercado(
            vetor, vetor_mercado, vetor_secao_skills=secs["skills"]
        )
        score_curriculo = calcular_score_curriculo(
            score_rh, score_mercado, vaga.peso_rh, vaga.peso_mercado, bonus
        )

        explicacao = gerar_explicacao(
            score_rh, score_mercado, score_curriculo,
            vaga.peso_rh, vaga.peso_mercado,
            features_cv   = feat_cv,
            features_vaga = feat_vaga,
        )

        # Verificação de nome (aviso suave — não bloqueia)
        nome_candidato = candidatura.candidato.nome if candidatura.candidato else ""
        verif_nome = _verificar_nome_cv(nome_candidato, texto)
        if not verif_nome["match"]:
            logger.warning(
                f"candidatura={candidatura_id} | nome no CV pode divergir do cadastro | "
                f"cadastrado='{verif_nome['nome_cadastrado']}' "
                f"confianca={verif_nome['confianca']} "
                f"ausentes={verif_nome['tokens_ausentes']}"
            )
            hist = list(candidatura.historico or [])
            hist.append({
                "de"    : candidatura.status.value,
                "para"  : candidatura.status.value,
                "ator"  : "sistema",
                "em"    : datetime.utcnow().isoformat(),
                "alerta": "nome_cv_divergente",
                "detalhe": (
                    f"Nome cadastrado '{verif_nome['nome_cadastrado']}' não foi encontrado "
                    f"no início do CV. Tokens ausentes: {', '.join(verif_nome['tokens_ausentes'])}. "
                    f"Verifique se o CV pertence a este candidato."
                ),
            })
            candidatura.historico = hist
        explicacao["alerta_nome"] = verif_nome

        curriculo = db.query(Curriculo).filter(
            Curriculo.candidatura_id == candidatura_id
        ).first()
        if not curriculo:
            curriculo = Curriculo(candidatura_id=candidatura_id)
            db.add(curriculo)

        curriculo.texto_extraido      = texto
        curriculo.vetor_embedding     = vetor
        curriculo.vetor_secao_exp     = secs["exp"]
        curriculo.vetor_secao_skills  = secs["skills"]
        curriculo.score_rh        = round(score_rh * 100, 1)
        curriculo.score_mercado   = round(score_mercado * 100, 1)
        curriculo.score_curriculo = score_curriculo
        curriculo.explicacao      = explicacao
        curriculo.processado_em   = datetime.utcnow()

        if candidatura.status == StatusCandidatura.PROCESSANDO:
            _transicionar(candidatura, StatusCandidatura.TRIAGEM_PENDENTE)
        candidatura.score_total = calcular_score_final(
            score_curriculo,
            candidatura.score_entrevista_rh,
            candidatura.score_entrevista_tec,
            vaga.peso_curriculo,
            vaga.peso_entrevista_rh,
            vaga.peso_entrevista_tec,
        )

        db.commit()
        logger.info(
            f"candidatura={candidatura_id} | vaga='{vaga.nome}' | "
            f"score_rh={round(score_rh*100,1)} score_mercado={round(score_mercado*100,1)} "
            f"score_curriculo={score_curriculo}"
        )

        _notificar_rh(db, vaga, candidatura, score_curriculo, explicacao)

        return {
            "status"         : "ok",
            "candidatura_id" : candidatura_id,
            "score_curriculo": score_curriculo,
        }

    except ValueError as exc:
        logger.error(f"candidatura={candidatura_id} | ERRO irrecuperável (sem retry): {exc}")
        db.rollback()
        try:
            cand = db.query(Candidatura).filter(Candidatura.id == candidatura_id).first()
            if cand:
                hist = list(cand.historico or [])
                hist.append({
                    "de"  : cand.status.value,
                    "para": StatusCandidatura.NOVO.value,
                    "ator": "sistema",
                    "em"  : datetime.utcnow().isoformat(),
                    "erro": str(exc),
                })
                cand.historico = hist
                cand.status    = StatusCandidatura.NOVO
                db.commit()
        except Exception:
            db.rollback()

    except Exception as exc:
        logger.error(f"candidatura={candidatura_id} | ERRO no processamento de texto: {exc}", exc_info=True)
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()


@celery_app.task
def reprocessar_todos_curriculos():
    """
    Reprocessa todos os currículos com texto extraído usando o modelo de
    embedding atual. Necessário após trocar EMBEDDING_MODEL no .env.

    Execute via: docker compose exec worker celery -A app.core.celery_app call app.ai.tasks.reprocessar_todos_curriculos
    Ou via API:  POST /admin/reprocessar-curriculos  (apenas admin)
    """
    db = SessionLocal()
    try:
        curriculos = (
            db.query(Curriculo)
            .filter(Curriculo.texto_extraido.isnot(None))
            .all()
        )
        total = len(curriculos)
        logger.info(f"reprocessar_todos_curriculos | {total} currículos para reprocessar")

        for i, cur in enumerate(curriculos, 1):
            try:
                processar_curriculo_texto.delay(
                    str(cur.candidatura_id),
                    cur.texto_extraido,
                )
                if i % 10 == 0:
                    logger.info(f"reprocessar | {i}/{total} enfileirados")
            except Exception as exc:
                logger.warning(f"reprocessar | curriculo {cur.id} falhou ao enfileirar: {exc}")

        logger.info(f"reprocessar_todos_curriculos | {total} tasks enfileiradas")
        return {"enfileirados": total}
    finally:
        db.close()
