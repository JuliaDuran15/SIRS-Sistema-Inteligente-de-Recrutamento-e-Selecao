import numpy as np


def _cos(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def calcular_score_rh_multi_secao(
    vetor_embedding : list[float],
    vetor_vaga      : list[float],
    vetor_secao_exp : list[float] | None = None,
) -> float:
    """
    Similaridade semântica CV↔vaga (sem bônus estrutural).

    Com seção de experiência:
      60% × sim(exp_section, vaga) + 40% × sim(full_cv, vaga)
    Sem seção:
      100% × sim(full_cv, vaga)

    O bônus estrutural é calculado externamente e aplicado ao score
    combinado final em calcular_score_curriculo, garantindo que corrija
    tanto o componente RH quanto o componente mercado.
    """
    if vetor_secao_exp is not None:
        return 0.60 * _cos(vetor_secao_exp, vetor_vaga) + 0.40 * _cos(vetor_embedding, vetor_vaga)
    return _cos(vetor_embedding, vetor_vaga)


def calcular_score_rh(
    vetor_curriculo : list[float],
    vetor_vaga      : list[float],
) -> float:
    """Similaridade semântica CV↔vaga (sem bônus estrutural)."""
    return _cos(vetor_curriculo, vetor_vaga)


def calcular_score_mercado(
    vetor_curriculo    : list[float],
    vetor_mercado      : list[float],
    vetor_secao_skills : list[float] | None = None,
) -> float:
    """
    Score de aderência ao mercado.

    Com seção de habilidades:
      60% × sim(skills_section, mercado)  ← alinhamento técnico focado
      40% × sim(full_cv, mercado)         ← contexto holístico

    Sem seção:
      100% × sim(full_cv, mercado)
    """
    if vetor_secao_skills is not None:
        return 0.60 * _cos(vetor_secao_skills, vetor_mercado) + 0.40 * _cos(vetor_curriculo, vetor_mercado)
    return _cos(vetor_curriculo, vetor_mercado)


def calcular_score_curriculo(
    score_rh         : float,
    score_mercado    : float,
    peso_rh          : float,
    peso_mercado     : float,
    bonus_estrutural : float = 0.0,
) -> float:
    """
    Combina os scores semânticos com o bônus estrutural.

    O bônus é aplicado ao score combinado (não só ao componente RH),
    garantindo que sinais estruturais (experiência, senioridade, skills)
    corrijam o resultado final independentemente do peso de cada componente.
    """
    score = (score_rh * peso_rh) + (score_mercado * peso_mercado) + bonus_estrutural
    return round(max(0.0, min(1.0, score)) * 100, 1)


def gerar_explicacao(
    score_rh         : float,
    score_mercado    : float,
    score_curriculo  : float,
    peso_rh          : float,
    peso_mercado     : float,
    features_cv      : dict | None = None,
    features_vaga    : dict | None = None,
    bonus_estrutural : float = 0.0,
) -> dict:
    def classificar(score: float) -> str:
        if score >= 0.80:
            return "excelente"
        if score >= 0.65:
            return "bom"
        if score >= 0.50:
            return "regular"
        return "baixo"

    contrib_rh      = round(score_rh * peso_rh * 100, 1)
    contrib_mercado = round(score_mercado * peso_mercado * 100, 1)

    resultado: dict = {
        "score_final"     : score_curriculo,
        "bonus_estrutural": round(bonus_estrutural * 100, 1),
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
        # Usa apenas skills do texto dos requisitos (não termos de mercado) para o display.
        hab_vaga_display = features_vaga.get("habilidades_texto") or features_vaga.get("habilidades", set())
        hab_cv = features_cv.get("habilidades", set())
        resultado["sinais_estruturais"]["habilidades_em_comum"] = sorted(hab_cv & hab_vaga_display)
        resultado["sinais_estruturais"]["habilidades_ausentes"]  = sorted(hab_vaga_display - hab_cv)

    return resultado


def calcular_score_final(
    score_curriculo     : float,
    score_entrevista_rh : float | None,
    score_entrevista_tec: float | None,
    peso_curriculo      : float,
    peso_entrevista_rh  : float,
    peso_entrevista_tec : float,
) -> float:
    soma        = (score_curriculo / 100) * peso_curriculo
    peso_ativo  = peso_curriculo

    if score_entrevista_rh is not None:
        soma       += (score_entrevista_rh  / 10) * peso_entrevista_rh
        peso_ativo += peso_entrevista_rh

    if score_entrevista_tec is not None:
        soma       += (score_entrevista_tec / 10) * peso_entrevista_tec
        peso_ativo += peso_entrevista_tec

    return round((soma / peso_ativo) * 100, 1)