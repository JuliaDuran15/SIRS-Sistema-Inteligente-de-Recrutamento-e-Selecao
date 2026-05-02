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
from typing import Any

logger = logging.getLogger(__name__)

_reranker_model = None


def _get_reranker():
    """Carrega o cross-encoder na primeira chamada (lazy load)."""
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers.cross_encoder import CrossEncoder
        from app.core.config import settings
        logger.info("Carregando cross-encoder: %s", settings.RERANKER_MODEL)
        _reranker_model = CrossEncoder(
            settings.RERANKER_MODEL,
            max_length=512,
        )
        logger.info("Cross-encoder pronto.")
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

    if not candidaturas:
        return []

    cands = candidaturas[:top_n] if top_n else candidaturas

    # Prepara pares (texto_vaga, trecho_cv) para o cross-encoder
    pares: list[tuple[str, str]] = []
    for c in cands:
        texto_cv = c.get("texto_curriculo") or ""
        trecho   = texto_para_rerank(texto_cv) if texto_cv else ""
        pares.append((texto_vaga, trecho))

    try:
        reranker  = _get_reranker()
        scores    = reranker.predict(pares, show_progress_bar=False)
        # normalize para [0, 1] via sigmoid
        import numpy as np
        scores_norm = (1 / (1 + np.exp(-scores))).tolist()
    except Exception as exc:
        logger.error("Erro no cross-encoder: %s — retornando ordem original", exc)
        for c in cands:
            c["score_rerank"] = None
        return cands

    for c, score in zip(cands, scores_norm):
        c["score_rerank"] = round(float(score), 4)

    return sorted(cands, key=lambda c: c["score_rerank"] or 0, reverse=True)
