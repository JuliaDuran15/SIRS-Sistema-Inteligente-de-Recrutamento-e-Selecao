"""Testes unitários para as funções puras do matching engine."""
import pytest
import numpy as np
from app.ai.matching_engine import (
    calcular_score_rh,
    calcular_score_mercado,
    calcular_score_curriculo,
    gerar_explicacao,
    calcular_score_final,
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def vec_norm(values):
    """Cria vetor normalizado a partir de lista."""
    v = np.array(values, dtype=float)
    return (v / np.linalg.norm(v)).tolist()


# ── calcular_score_rh ─────────────────────────────────────────────────────────
class TestCalcularScoreRH:
    def test_vetores_identicos_retornam_1(self):
        v = vec_norm([1.0, 0.0, 0.0])
        assert calcular_score_rh(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_vetores_opostos_retornam_negativo(self):
        a = vec_norm([1.0, 0.0])
        b = vec_norm([-1.0, 0.0])
        assert calcular_score_rh(a, b) < 0

    def test_vetores_ortogonais_retornam_zero(self):
        a = vec_norm([1.0, 0.0])
        b = vec_norm([0.0, 1.0])
        assert calcular_score_rh(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_resultado_e_float(self):
        v = [0.5] * 4
        assert isinstance(calcular_score_rh(v, v), float)

    def test_score_alta_similaridade(self):
        base = vec_norm([0.8, 0.6, 0.0])
        similar = vec_norm([0.7, 0.7, 0.1])
        assert calcular_score_rh(base, similar) > 0.9


# ── calcular_score_mercado ────────────────────────────────────────────────────
class TestCalcularScoreMercado:
    def test_mesmo_comportamento_que_score_rh(self):
        a = vec_norm([1.0, 2.0, 3.0])
        b = vec_norm([1.0, 2.0, 3.0])
        assert calcular_score_mercado(a, b) == pytest.approx(calcular_score_rh(a, b))

    def test_vetores_diferentes(self):
        a = vec_norm([1.0, 0.0, 0.0])
        b = vec_norm([0.0, 1.0, 0.0])
        assert calcular_score_mercado(a, b) == pytest.approx(0.0, abs=1e-6)


# ── calcular_score_curriculo ──────────────────────────────────────────────────
class TestCalcularScoreCurriculo:
    def test_scores_maximos(self):
        # score_rh=1.0, score_mercado=1.0, pesos somam 1.0 → 100.0
        result = calcular_score_curriculo(1.0, 1.0, 0.6, 0.4)
        assert result == pytest.approx(100.0)

    def test_scores_minimos(self):
        result = calcular_score_curriculo(0.0, 0.0, 0.6, 0.4)
        assert result == pytest.approx(0.0)

    def test_pesos_aplicados_corretamente(self):
        # score_rh=1.0, score_mercado=0.0, peso_rh=0.6 → 60.0
        result = calcular_score_curriculo(1.0, 0.0, 0.6, 0.4)
        assert result == pytest.approx(60.0)

    def test_pesos_invertidos(self):
        result = calcular_score_curriculo(0.0, 1.0, 0.6, 0.4)
        assert result == pytest.approx(40.0)

    def test_resultado_arredondado_uma_casa(self):
        result = calcular_score_curriculo(0.333, 0.666, 0.6, 0.4)
        # verifica que tem no máximo 1 casa decimal
        assert result == round(result, 1)

    def test_resultado_e_float(self):
        assert isinstance(calcular_score_curriculo(0.5, 0.5, 0.6, 0.4), float)


# ── gerar_explicacao ──────────────────────────────────────────────────────────
class TestGerarExplicacao:
    def _explicacao(self, rh=0.8, mkt=0.7, curriculo=74.0, p_rh=0.6, p_mkt=0.4):
        return gerar_explicacao(rh, mkt, curriculo, p_rh, p_mkt)

    def test_retorna_dict_com_chaves_esperadas(self):
        exp = self._explicacao()
        assert "score_final" in exp
        assert "componentes" in exp
        assert "resumo" in exp

    def test_score_final_preservado(self):
        exp = self._explicacao(curriculo=74.0)
        assert exp["score_final"] == 74.0

    def test_componentes_tem_aderencia_vaga_e_mercado(self):
        exp = self._explicacao()
        assert "aderencia_vaga" in exp["componentes"]
        assert "aderencia_mercado" in exp["componentes"]

    def test_classificacao_excelente(self):
        exp = self._explicacao(rh=0.85)
        assert exp["componentes"]["aderencia_vaga"]["classificacao"] == "excelente"

    def test_classificacao_bom(self):
        exp = self._explicacao(rh=0.70)
        assert exp["componentes"]["aderencia_vaga"]["classificacao"] == "bom"

    def test_classificacao_regular(self):
        exp = self._explicacao(rh=0.55)
        assert exp["componentes"]["aderencia_vaga"]["classificacao"] == "regular"

    def test_classificacao_baixo(self):
        exp = self._explicacao(rh=0.30)
        assert exp["componentes"]["aderencia_vaga"]["classificacao"] == "baixo"

    def test_contribuicoes_somam_score_curriculo(self):
        rh, mkt, p_rh, p_mkt = 0.8, 0.7, 0.6, 0.4
        esperado = calcular_score_curriculo(rh, mkt, p_rh, p_mkt)
        exp = self._explicacao(rh=rh, mkt=mkt, curriculo=esperado, p_rh=p_rh, p_mkt=p_mkt)
        contrib_rh  = exp["componentes"]["aderencia_vaga"]["contribuicao"]
        contrib_mkt = exp["componentes"]["aderencia_mercado"]["contribuicao"]
        assert contrib_rh + contrib_mkt == pytest.approx(esperado, abs=0.5)

    def test_resumo_e_string(self):
        assert isinstance(self._explicacao()["resumo"], str)

    def test_resumo_contem_score(self):
        exp = self._explicacao(curriculo=74.0)
        assert "74.0" in exp["resumo"]


# ── calcular_score_final ──────────────────────────────────────────────────────
class TestCalcularScoreFinal:
    def test_sem_entrevistas_usa_apenas_curriculo(self):
        # score_curriculo=80, peso_curriculo=0.5 → contribuição = 40
        # entrevistas None → contribuem 0
        result = calcular_score_final(80.0, None, None, 0.5, 0.25, 0.25)
        assert result == pytest.approx(40.0)

    def test_todas_notas_maximas(self):
        # curriculo=100/100=1.0, entrev_rh=10/10=1.0, entrev_tec=10/10=1.0
        # pesos somam 1.0 → score=100.0
        result = calcular_score_final(100.0, 10.0, 10.0, 0.5, 0.25, 0.25)
        assert result == pytest.approx(100.0)

    def test_apenas_rh_preenchida(self):
        # curriculo=60, entrev_rh=8, entrev_tec=None
        # (0.6*0.5) + (0.8*0.25) + (0*0.25) = 0.3 + 0.2 + 0 = 0.5 → 50.0
        result = calcular_score_final(60.0, 8.0, None, 0.5, 0.25, 0.25)
        assert result == pytest.approx(50.0)

    def test_pesos_diferentes(self):
        result = calcular_score_final(80.0, 6.0, 4.0, 0.6, 0.2, 0.2)
        # (0.8*0.6) + (0.6*0.2) + (0.4*0.2) = 0.48+0.12+0.08 = 0.68 → 68.0
        assert result == pytest.approx(68.0)

    def test_resultado_arredondado(self):
        result = calcular_score_final(33.3, 5.5, 7.7, 0.5, 0.25, 0.25)
        assert result == round(result, 1)

    def test_resultado_e_float(self):
        assert isinstance(calcular_score_final(50.0, 5.0, 5.0, 0.5, 0.25, 0.25), float)
