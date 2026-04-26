"""Testes unitários para funções puras do market_analyzer."""
import pytest
from app.ai.market_analyzer import (
    detectar_categoria,
    limpar_skills_desc,
    extrair_de_adzuna,
    extrair_de_kaggle,
)


# ── detectar_categoria ────────────────────────────────────────────────────────
class TestDetectarCategoria:
    def test_desenvolvedor_python(self):
        assert detectar_categoria("Desenvolvedor Python Sênior") == "tech"

    def test_advogado_tributarista(self):
        assert detectar_categoria("Advogado Tributarista") == "direito"

    def test_analista_rh(self):
        assert detectar_categoria("Analista de RH Recrutamento e Seleção") == "rh"

    def test_engenheiro_civil(self):
        assert detectar_categoria("Engenheiro Civil — Obras") == "engenharia_civil"

    def test_engenheiro_mecanico(self):
        assert detectar_categoria("Engenheiro Mecânico de Produção") == "engenharia_geral"

    def test_medico(self):
        assert detectar_categoria("Médico Clínico Geral") == "saude"

    def test_contador(self):
        assert detectar_categoria("Contador Financeiro") == "financeiro"

    def test_marketing(self):
        assert detectar_categoria("Analista de Marketing Digital") == "marketing"

    def test_desconhecido_retorna_tech_padrao(self):
        assert detectar_categoria("Cargo Sem Categoria Definida XYZW") == "tech"

    def test_case_insensitive(self):
        assert detectar_categoria("DESENVOLVEDOR JAVA BACKEND") == "tech"

    def test_acento_normalizado(self):
        # "jurídico" com acento deve bater em "juridico"
        assert detectar_categoria("Analista Jurídico Senior") == "direito"

    def test_fullstack(self):
        assert detectar_categoria("Desenvolvedor Fullstack React + Node") == "tech"

    def test_devops(self):
        assert detectar_categoria("DevOps Engineer Kubernetes") == "tech"


# ── limpar_skills_desc ────────────────────────────────────────────────────────
class TestLimparSkillsDesc:
    def test_lista_simples_com_virgula(self):
        result = limpar_skills_desc("Python,Docker,AWS")
        assert "python" in result
        assert "docker" in result
        assert "aws" in result

    def test_espacos_em_branco_removidos(self):
        result = limpar_skills_desc("Python, Docker, AWS")
        assert "python" in result

    def test_frases_longas_ignoradas(self):
        longa = "We are looking for a talented engineer with experience" * 2
        result = limpar_skills_desc(longa)
        # A frase tem mais de 50 chars → não deve aparecer
        for item in result:
            assert len(item) <= 50

    def test_artigos_em_ingles_ignorados(self):
        result = limpar_skills_desc("the, a, an, Python, Docker")
        assert "the" not in result
        assert "python" in result

    def test_muito_curto_ignorado(self):
        result = limpar_skills_desc("a,b,Python")
        # "a" e "b" têm menos de 2 chars → ignorados
        for item in result:
            assert len(item) >= 2

    def test_retorna_lista(self):
        assert isinstance(limpar_skills_desc("Python,Java"), list)

    def test_string_vazia_retorna_lista_vazia(self):
        result = limpar_skills_desc("")
        assert result == []


# ── extrair_de_kaggle ─────────────────────────────────────────────────────────
class TestExtrairDeKaggle:
    def test_retorna_lista_de_tuplas(self):
        textos = ["Python,Docker,AWS", "Python,Kubernetes", "Python,Redis"]
        result = extrair_de_kaggle(textos)
        assert isinstance(result, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in result)

    def test_skill_mais_frequente_primeiro(self):
        textos = ["Python,Docker", "Python,AWS", "Python,Redis"]
        result = extrair_de_kaggle(textos)
        # Python aparece 3x, outros 1x cada
        assert result[0][0] == "python"

    def test_stopwords_excluidas(self):
        textos = ["and,the,Python", "Python,or"]
        result = extrair_de_kaggle(textos)
        termos = [t[0] for t in result]
        assert "and" not in termos
        assert "the" not in termos

    def test_top_n_respeitado(self):
        textos = [f"skill{i}" for i in range(50)]
        result = extrair_de_kaggle(textos, top_n=10)
        assert len(result) <= 10

    def test_texto_vazio_retorna_vazio(self):
        result = extrair_de_kaggle([])
        assert result == []


# ── extrair_de_adzuna ─────────────────────────────────────────────────────────
class TestExtrairDeAdzuna:
    def _textos_tech(self):
        return [
            "Desenvolvedor Python com experiência em Docker e AWS",
            "Vaga para engenheiro Python, Docker e Kubernetes",
            "Requisitos: Python, PostgreSQL e Redis",
            "Python developer, experiência com microservices e Docker",
            "Buscamos Python sênior com AWS e CI/CD",
        ]

    def test_retorna_lista_de_tuplas(self):
        result = extrair_de_adzuna(self._textos_tech())
        assert isinstance(result, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in result)

    def test_skill_presente_nos_resultados(self):
        result = extrair_de_adzuna(self._textos_tech())
        termos = [t[0] for t in result]
        # Python está em todos os textos → deve aparecer
        assert "python" in termos

    def test_top_n_respeitado(self):
        result = extrair_de_adzuna(self._textos_tech(), top_n=5)
        assert len(result) <= 5

    def test_termos_genericos_excluidos(self):
        textos = [
            "Benefícios: vale transporte, plano de saúde, CLT",
            "Regime CLT com FGTS e INSS",
        ]
        result = extrair_de_adzuna(textos)
        termos = [t[0] for t in result]
        # Termos como "clt", "fgts", "inss" devem ser filtrados
        assert "clt" not in termos
        assert "fgts" not in termos

    def test_texto_vazio_retorna_vazio(self):
        result = extrair_de_adzuna([])
        assert result == []

    def test_scores_sao_inteiros(self):
        result = extrair_de_adzuna(self._textos_tech())
        for _, score in result:
            assert isinstance(score, int)
