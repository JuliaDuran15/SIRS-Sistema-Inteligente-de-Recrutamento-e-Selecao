import numpy as np


def _cos(a: list[float], b: list[float]) -> float:
    return float(np.dot(np.array(a), np.array(b)))


def calcular_score_rh_multi_secao(
    vetor_embedding    : list[float],
    vetor_vaga         : list[float],
    vetor_mercado      : list[float],
    vetor_secao_exp    : list[float] | None = None,
    vetor_secao_skills : list[float] | None = None,
    texto_curriculo    : str | None = None,
    texto_vaga         : str | None = None,
    formacao           : list | None = None,
    termos_mercado     : list | None = None,
) -> float:
    """
    Score de aderência usando vetores de seção quando disponíveis.

    Com seções (CV bem estruturado):
      45% × sim(exp_section, vaga_req)   ← compatibilidade direta
      30% × sim(full_cv, vaga_req)       ← holística
      25% × sim(skills_section, mercado) ← skills vs tendência mercado

    Sem seções (fallback):
      Usa calcular_score_rh padrão + bônus estrutural.
    """
    tem_secoes = vetor_secao_exp is not None or vetor_secao_skills is not None

    if tem_secoes:
        # Componente experiência
        sim_exp = _cos(vetor_secao_exp, vetor_vaga) if vetor_secao_exp else _cos(vetor_embedding, vetor_vaga)
        # Componente holístico
        sim_full = _cos(vetor_embedding, vetor_vaga)
        # Componente skills vs mercado
        sim_skills = _cos(vetor_secao_skills, vetor_mercado) if vetor_secao_skills else _cos(vetor_embedding, vetor_mercado)

        score = 0.45 * sim_exp + 0.30 * sim_full + 0.25 * sim_skills

        # Bônus estrutural (menor peso quando já temos seções — seções são mais precisas)
        if texto_curriculo and texto_vaga:
            from app.ai.feature_extractor import (
                extrair_features_curriculo, extrair_features_vaga, calcular_bonus_estrutural,
            )
            feat_cv   = extrair_features_curriculo(texto_curriculo, formacao)
            feat_vaga = extrair_features_vaga(texto_vaga, termos_mercado)
            bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga) * 0.6  # peso reduzido
            score     = max(0.0, min(1.0, score + bonus))

        return score

    # Fallback: scoring padrão com bônus estrutural total
    return calcular_score_rh(
        vetor_embedding, vetor_vaga,
        texto_curriculo=texto_curriculo,
        texto_vaga=texto_vaga,
        formacao=formacao,
        termos_mercado=termos_mercado,
    )


def calcular_score_rh(
    vetor_curriculo : list[float],
    vetor_vaga      : list[float],
    texto_curriculo : str | None = None,
    texto_vaga      : str | None = None,
    formacao        : list | None = None,
    termos_mercado  : list | None = None,
) -> float:
    """
    Score de aderência aos requisitos da vaga.

    Quando texto_curriculo e texto_vaga são fornecidos, aplica um bônus
    estrutural baseado em anos de experiência, senioridade e overlap de
    habilidades (±15% sobre a similaridade semântica base).
    """
    sim = _cos(vetor_curriculo, vetor_vaga)

    if texto_curriculo and texto_vaga:
        from app.ai.feature_extractor import (
            extrair_features_curriculo,
            extrair_features_vaga,
            calcular_bonus_estrutural,
        )
        feat_cv   = extrair_features_curriculo(texto_curriculo, formacao)
        feat_vaga = extrair_features_vaga(texto_vaga, termos_mercado)
        bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga)
        return max(0.0, min(1.0, sim + bonus))

    return sim


def calcular_score_mercado(
    vetor_curriculo: list[float],
    vetor_mercado  : list[float],
) -> float:
    return _cos(vetor_curriculo, vetor_mercado)


def calcular_score_curriculo(
    score_rh: float,
    score_mercado: float,
    peso_rh: float,
    peso_mercado: float,
) -> float:
    score = (score_rh * peso_rh) + (score_mercado * peso_mercado)
    return round(score * 100, 1)


def gerar_explicacao(
    score_rh        : float,
    score_mercado   : float,
    score_curriculo : float,
    peso_rh         : float,
    peso_mercado    : float,
    features_cv     : dict | None = None,
    features_vaga   : dict | None = None,
) -> dict:
    def classificar(score: float) -> str:
        if score >= 0.80: return "excelente"
        if score >= 0.65: return "bom"
        if score >= 0.50: return "regular"
        return "baixo"

    contrib_rh      = round(score_rh * peso_rh * 100, 1)
    contrib_mercado = round(score_mercado * peso_mercado * 100, 1)

    resultado: dict = {
        "score_final": score_curriculo,
        "componentes": {
            "aderencia_vaga": {
                "score"        : round(score_rh * 100, 1),
                "peso"         : f"{int(peso_rh * 100)}%",
                "contribuicao" : contrib_rh,
                "classificacao": classificar(score_rh),
            },
            "aderencia_mercado": {
                "score"        : round(score_mercado * 100, 1),
                "peso"         : f"{int(peso_mercado * 100)}%",
                "contribuicao" : contrib_mercado,
                "classificacao": classificar(score_mercado),
            },
        },
        "resumo": (
            f"Score {score_curriculo}/100 — "
            f"{contrib_rh} pts da vaga e {contrib_mercado} pts do mercado."
        ),
    }

    # Inclui sinais estruturais na explicação quando disponíveis
    if features_cv:
        resultado["sinais_estruturais"] = {
            "anos_experiencia" : features_cv.get("anos_experiencia", 0),
            "nivel_senioridade": features_cv.get("nivel_senioridade", 0),
            "habilidades"      : sorted(features_cv.get("habilidades", set())),
            "nivel_educacao"   : features_cv.get("nivel_educacao", 0),
        }
    if features_cv and features_vaga:
        overlap = features_cv.get("habilidades", set()) & features_vaga.get("habilidades", set())
        resultado["sinais_estruturais"]["habilidades_em_comum"] = sorted(overlap)

    return resultado


def calcular_score_final(
    score_curriculo     : float,
    score_entrevista_rh : float | None,
    score_entrevista_tec: float | None,
    peso_curriculo      : float,
    peso_entrevista_rh  : float,
    peso_entrevista_tec : float,
) -> float:
    sc  = score_curriculo / 100
    srh = (score_entrevista_rh  / 10) if score_entrevista_rh  is not None else 0.0
    stc = (score_entrevista_tec / 10) if score_entrevista_tec is not None else 0.0

    score = (sc * peso_curriculo) + (srh * peso_entrevista_rh) + (stc * peso_entrevista_tec)
    return round(score * 100, 1)