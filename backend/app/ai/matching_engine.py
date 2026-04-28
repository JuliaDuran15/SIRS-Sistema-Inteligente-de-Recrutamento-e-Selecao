import numpy as np


def calcular_score_rh(
    vetor_curriculo: list[float],
    vetor_vaga: list[float],
) -> float:
    a = np.array(vetor_curriculo)
    b = np.array(vetor_vaga)
    return float(np.dot(a, b))


def calcular_score_mercado(
    vetor_curriculo: list[float],
    vetor_mercado: list[float],
) -> float:
    a = np.array(vetor_curriculo)
    b = np.array(vetor_mercado)
    return float(np.dot(a, b))


def calcular_score_curriculo(
    score_rh: float,
    score_mercado: float,
    peso_rh: float,
    peso_mercado: float,
) -> float:
    score = (score_rh * peso_rh) + (score_mercado * peso_mercado)
    return round(score * 100, 1)


def gerar_explicacao(
    score_rh: float,
    score_mercado: float,
    score_curriculo: float,
    peso_rh: float,
    peso_mercado: float,
) -> dict:
    def classificar(score: float) -> str:
        if score >= 0.80: return "excelente"
        if score >= 0.65: return "bom"
        if score >= 0.50: return "regular"
        return "baixo"

    contrib_rh      = round(score_rh * peso_rh * 100, 1)
    contrib_mercado = round(score_mercado * peso_mercado * 100, 1)

    return {
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