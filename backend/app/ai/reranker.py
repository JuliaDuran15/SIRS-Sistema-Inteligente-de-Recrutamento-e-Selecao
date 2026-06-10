"""
Cross-encoder (reranker) para reordenação precisa de candidaturas.

Fluxo:
  1. Bi-encoder já computou score_curriculo (rápido, para todos os candidatos)
  2. Cross-encoder recebe os top-N e reordena com muito mais precisão

Por que o cross-encoder é melhor:
  - Bi-encoder: encode(CV) e encode(Vaga) separadamente → perde interações
  - Cross-encoder: encode(CV + Vaga juntos) → captura "Python na vaga + Python no CV"

Limitação: O modelo tem limite de ~512 tokens, então usamos apenas os
trechos mais relevantes do CV (resumo + experiência + skills, ≤800 chars).
"""
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)

_reranker_model = None


def _get_reranker():
    """Carrega o cross-encoder na primeira chamada (lazy load)."""
    global _reranker_model
    if _reranker_model is None:
        from app.core.config import settings
        from sentence_transformers.cross_encoder import CrossEncoder
        logger.info("Carregando cross-encoder: %s", settings.RERANKER_MODEL)
        t0 = time.perf_counter()
        _reranker_model = CrossEncoder(settings.RERANKER_MODEL, max_length=512)
        logger.info("Cross-encoder pronto em %.1fs.", time.perf_counter() - t0)
    return _reranker_model


def rerankar(
    texto_vaga   : str,
    candidaturas : list[dict],   # [{id, texto_curriculo, ...}]
    top_n        : int | None = None,
) -> list[dict]:
    """
    Reordena candidaturas pelo cross-encoder e injeta 'score_rerank' em cada item.

    Args:
        texto_vaga:   requisitos da vaga (usado como query do cross-encoder)
        candidaturas: lista de dicts com ao menos 'id' e 'texto_curriculo'
        top_n:        se informado, processa somente os top-N (mais eficiente)

    Returns:
        A mesma lista ordenada do maior para o menor score_rerank,
        com o campo 'score_rerank' adicionado (0–1).
    """
    from app.ai.section_extractor import texto_para_rerank

    t_inicio = time.perf_counter()
    total_entrada = len(candidaturas)

    if not candidaturas:
        logger.info("rerankar: nenhuma candidatura recebida, retornando vazio.")
        return []

    cands = candidaturas[:top_n] if top_n else candidaturas
    n = len(cands)

    logger.info(
        "rerankar: iniciando — %d candidatura(s) de entrada, top_n=%s, processando %d. "
        "Vaga: '%s...'",
        total_entrada, top_n, n, texto_vaga[:80],
    )

    # Prepara pares (texto_vaga, trecho_cv) para o cross-encoder
    pares: list[tuple[str, str]] = []
    sem_curriculo = 0
    for c in cands:
        texto_cv = c.get("texto_curriculo") or ""
        if not texto_cv:
            sem_curriculo += 1
        trecho = texto_para_rerank(texto_cv) if texto_cv else ""
        pares.append((texto_vaga, trecho))

    if sem_curriculo:
        logger.warning("rerankar: %d candidatura(s) sem texto de currículo.", sem_curriculo)

    logger.debug("rerankar: %d par(es) prontos para o cross-encoder.", len(pares))

    try:
        reranker = _get_reranker()

        t_predict = time.perf_counter()
        scores_raw = reranker.predict(pares, show_progress_bar=False)
        logger.debug(
            "rerankar: predict concluído em %.2fs. Scores brutos — min=%.3f, max=%.3f, média=%.3f.",
            time.perf_counter() - t_predict,
            float(np.min(scores_raw)),
            float(np.max(scores_raw)),
            float(np.mean(scores_raw)),
        )

        scores_norm = (1 / (1 + np.exp(-scores_raw))).tolist()
        logger.debug(
            "rerankar: scores normalizados (sigmoid) — min=%.3f, max=%.3f, média=%.3f.",
            min(scores_norm), max(scores_norm),
            sum(scores_norm) / len(scores_norm),
        )
    except Exception as exc:
        logger.error(
            "rerankar: erro no cross-encoder após %.2fs: %s — retornando ordem original.",
            time.perf_counter() - t_inicio, exc,
        )
        for c in cands:
            c["score_rerank"] = None
        return cands

    for c, score in zip(cands, scores_norm):
        c["score_rerank"] = round(float(score), 4)

    resultado = sorted(cands, key=lambda c: c["score_rerank"] or 0, reverse=True)

    top5 = [(r.get("id"), r["score_rerank"]) for r in resultado[:5]]
    logger.info(
        "rerankar: concluído em %.2fs. Top-5 (id, score): %s",
        time.perf_counter() - t_inicio, top5,
    )

    return resultado
