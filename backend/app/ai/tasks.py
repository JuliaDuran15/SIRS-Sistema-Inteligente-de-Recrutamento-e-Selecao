import asyncio
from datetime import datetime

import app.db.base  # noqa: F401 — garante que todos os models estão mapeados
from app.ai.market_analyzer import analisar_mercado
from app.ai.matching_engine import (
    calcular_score_curriculo,
    calcular_score_mercado,
    calcular_score_rh,
    calcular_score_rh_multi_secao,
    gerar_explicacao,
)
from app.ai.resume_parser import parsear_curriculo, vetorizar_texto, vetorizar_secoes
from app.core.celery_app import celery_app
from app.core.logger import get_logger
from app.db.session import SessionLocal
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.vaga import Vaga

logger = get_logger("TASKS")


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

        # 2. Parseia o currículo — extrai texto e gera vetor
        resultado = parsear_curriculo(caminho_pdf)

        # 3. Vetores de seção (experiência e habilidades)
        vetor_exp    = resultado.get("vetor_secao_exp")
        vetor_skills = resultado.get("vetor_secao_skills")

        # 4. Calcula scores — multi-seção quando disponível, fallback holístico
        termos        = (vaga.ranking_mercado or {}).get("termos")
        vetor_mercado = vaga.vetor_mercado if vaga.vetor_mercado is not None else vaga.vetor_vaga

        score_rh = calcular_score_rh_multi_secao(
            vetor_embedding = resultado["vetor_embedding"],
            vetor_vaga      = vaga.vetor_vaga,
            vetor_secao_exp = vetor_exp,
            texto_curriculo = resultado["texto_extraido"],
            texto_vaga      = vaga.requisitos_texto,
            termos_mercado  = termos,
        )
        score_mercado = calcular_score_mercado(
            resultado["vetor_embedding"], vetor_mercado, vetor_secao_skills=vetor_skills
        )
        score_curriculo = calcular_score_curriculo(
            score_rh, score_mercado, vaga.peso_rh, vaga.peso_mercado
        )

        # 5. Explicação XAI com sinais estruturais
        from app.ai.feature_extractor import extrair_features_curriculo, extrair_features_vaga
        feat_cv   = extrair_features_curriculo(resultado["texto_extraido"])
        feat_vaga = extrair_features_vaga(vaga.requisitos_texto, termos)
        explicacao = gerar_explicacao(
            score_rh, score_mercado, score_curriculo,
            vaga.peso_rh, vaga.peso_mercado,
            features_cv   = feat_cv,
            features_vaga = feat_vaga,
        )

        # 5. Salva no banco
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
        curriculo.score_rh            = round(score_rh * 100, 1)
        curriculo.score_mercado    = round(score_mercado * 100, 1)
        curriculo.score_curriculo  = score_curriculo
        curriculo.processado_em    = datetime.utcnow()

        # Salva a explicação XAI na candidatura
        candidatura.historico = (candidatura.historico or []) + [{
            "evento"    : "curriculo_processado",
            "em"        : datetime.utcnow().isoformat(),
            "explicacao": explicacao,
        }]
        candidatura.status = StatusCandidatura.TRIAGEM_PENDENTE

        db.commit()
        logger.info(
            f"candidatura={candidatura_id} | vaga='{vaga.nome}' | "
            f"score_rh={round(score_rh*100,1)} score_mercado={round(score_mercado*100,1)} "
            f"score_curriculo={score_curriculo}"
        )

        return {
            "status"        : "ok",
            "candidatura_id": candidatura_id,
            "score_curriculo": score_curriculo,
        }

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

        return {
            "status"  : "ok",
            "vaga_id" : vaga_id,
            "termos"  : len(resultado["termos_frequentes"]),
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

        vetor  = vetorizar_texto(texto)
        secs   = vetorizar_secoes(texto)
        termos = (vaga.ranking_mercado or {}).get("termos")

        vetor_mercado = vaga.vetor_mercado if vaga.vetor_mercado is not None else vaga.vetor_vaga
        score_rh = calcular_score_rh_multi_secao(
            vetor_embedding = vetor,
            vetor_vaga      = vaga.vetor_vaga,
            vetor_secao_exp = secs["exp"],
            texto_curriculo = texto,
            texto_vaga      = vaga.requisitos_texto,
            termos_mercado  = termos,
        )
        score_mercado = calcular_score_mercado(
            vetor, vetor_mercado, vetor_secao_skills=secs["skills"]
        )
        score_curriculo = calcular_score_curriculo(
            score_rh, score_mercado, vaga.peso_rh, vaga.peso_mercado
        )

        from app.ai.feature_extractor import extrair_features_curriculo, extrair_features_vaga
        feat_cv   = extrair_features_curriculo(texto)
        feat_vaga = extrair_features_vaga(vaga.requisitos_texto, termos)
        explicacao = gerar_explicacao(
            score_rh, score_mercado, score_curriculo,
            vaga.peso_rh, vaga.peso_mercado,
            features_cv   = feat_cv,
            features_vaga = feat_vaga,
        )

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
        curriculo.processado_em   = datetime.utcnow()

        candidatura.historico = (candidatura.historico or []) + [{
            "evento"    : "curriculo_processado",
            "em"        : datetime.utcnow().isoformat(),
            "explicacao": explicacao,
        }]
        candidatura.status = StatusCandidatura.TRIAGEM_PENDENTE

        db.commit()
        logger.info(
            f"candidatura={candidatura_id} | vaga='{vaga.nome}' | "
            f"score_rh={round(score_rh*100,1)} score_mercado={round(score_mercado*100,1)} "
            f"score_curriculo={score_curriculo}"
        )
        return {
            "status"         : "ok",
            "candidatura_id" : candidatura_id,
            "score_curriculo": score_curriculo,
        }

    except Exception as exc:
        logger.error(f"candidatura={candidatura_id} | ERRO no processamento de texto: {exc}", exc_info=True)
        db.rollback()
        raise self.retry(exc=exc)

    finally:
        db.close()
