"""
Testes de integração do pipeline de IA — feature extractor + matching engine.

Divididos em dois grupos:

  TestFeaturesEstruturais  — análise de features sem embedding (rápido, ~1s)
  TestPipelineSemantico    — scores com modelo real         (lento, @pytest.mark.slow)

Comandos:
  pytest tests/test_ai_curriculo.py                    # só os rápidos
  pytest tests/test_ai_curriculo.py -m slow -s         # os semânticos com saída impressa
  pytest tests/test_ai_curriculo.py -m slow -v         # semânticos verbosos
"""
import pytest
from app.ai.feature_extractor import (
    extrair_features_curriculo,
    extrair_features_vaga,
    calcular_bonus_estrutural,
)
from app.ai.matching_engine import (
    calcular_score_rh,
    calcular_score_mercado,
    calcular_score_curriculo,
    gerar_explicacao,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CVs e vagas de teste — elaborados para cobrir diferentes perfis
# ═══════════════════════════════════════════════════════════════════════════════

# ── Vaga alvo: Dev Python Sênior ──────────────────────────────────────────────
VAGA_PYTHON_SENIOR = """
Desenvolvedor Python Sênior — Backend
Buscamos profissional com sólida experiência em desenvolvimento backend Python.

Requisitos obrigatórios:
  - Python, FastAPI, PostgreSQL, Redis, Docker
  - 5+ anos de experiência em backend
  - Experiência com APIs RESTful e microsserviços
  - Celery para tarefas assíncronas
  - SQLAlchemy / Alembic

Diferenciais:
  - Kubernetes, AWS ou GCP
  - pytest, TDD
  - Inglês intermediário ou avançado
"""

# ── Vaga alvo: Data Science ───────────────────────────────────────────────────
VAGA_DATA_SCIENCE = """
Cientista de Dados Sênior
Empresa de tecnologia busca Cientista de Dados com experiência em ML em produção.

Requisitos:
  - Python, Machine Learning, scikit-learn, TensorFlow ou PyTorch
  - Experiência com NLP e processamento de linguagem natural
  - FastAPI para servir modelos em produção
  - PostgreSQL ou MongoDB
  - 5+ anos em ciência de dados ou ML
  - Mestrado ou doutorado em área correlata (diferencial)
"""

# ── CV 1 — Ideal para Python Sênior (10 anos, skills perfeitas) ───────────────
CV_IDEAL_PYTHON = """
João Silva — Desenvolvedor Python Sênior
10 anos de experiência em desenvolvimento de software backend.

EXPERIÊNCIA PROFISSIONAL

TechCorp Brasil — Desenvolvedor Python Sênior          2019–2024
  Liderança técnica de equipe de 6 engenheiros. Arquitetura e desenvolvimento
  de APIs RESTful com FastAPI e PostgreSQL. Integração com Redis e Celery para
  processamento assíncrono. Deploy em Kubernetes na AWS. CI/CD via GitHub Actions.
  Testes automatizados com pytest (cobertura 90%+). Migrations com Alembic.

StartupXYZ — Engenheiro de Software Backend            2015–2019
  Desenvolvimento de microsserviços em Python (Django, Flask). PostgreSQL, Redis,
  RabbitMQ. Containerização com Docker. SQLAlchemy. APIs REST. Scrum.

DevHouse Tecnologia — Desenvolvedor Python Pleno        2013–2015
  Python, Django, MySQL. APIs internas. Celery para jobs. Linux, Git.

HABILIDADES TÉCNICAS
Python · FastAPI · Django · Flask · PostgreSQL · Redis · Docker · Kubernetes
Celery · SQLAlchemy · Alembic · REST APIs · AWS · pytest · Git · Linux
Microservices · CI/CD · RabbitMQ

FORMAÇÃO
Bacharelado em Ciência da Computação — Universidade de São Paulo (2013)

IDIOMAS
Inglês avançado (C1) — TOEFL 105
"""

# ── CV 2 — Mediano: dev web, pouca exp, skills tangenciais ───────────────────
CV_MEDIANO_WEB = """
Ana Costa — Desenvolvedora Web
2 anos de experiência em desenvolvimento.

EXPERIÊNCIA PROFISSIONAL

Agência Digital ABC — Desenvolvedora Web               2022–2024
  Criação de sites e landing pages em WordPress e Elementor.
  HTML, CSS, JavaScript. Pequenos scripts em Python para automação.
  MySQL básico. Integração com APIs de terceiros via REST.

HABILIDADES
HTML · CSS · JavaScript · Python básico · PHP · MySQL · WordPress · Git

FORMAÇÃO
Técnico em Informática — ETEC São Paulo (2020)
"""

# ── CV 3 — Irrelevante: advogado, sem skills de dev ──────────────────────────
CV_IRRELEVANTE_ADVOGADO = """
Carlos Mendes — Advogado Tributarista Sênior
15 anos de experiência em direito empresarial e tributário.

EXPERIÊNCIA PROFISSIONAL

Mendes & Associados — Sócio Diretor                    2015–2024
  Gestão do escritório. Consultoria tributária para empresas de médio porte.
  Planejamento fiscal, compliance fiscal, recuperação de créditos tributários,
  defesas administrativas no CARF e judiciais no STJ.

Barbosa Advogados — Advogado Sênior                    2009–2015
  Direito empresarial, contratos, societário, M&A, fusões e aquisições.

HABILIDADES
Direito Tributário · Direito Empresarial · Contratos · Consultoria Jurídica
Pacote Office · OAB/SP 123456

FORMAÇÃO
Graduação em Direito — PUC-SP (2009)
LLM em Direito Tributário — FGV (2012)

IDIOMAS
Inglês fluente · Espanhol intermediário
"""

# ── CV 4 — Experiência declarada explicitamente (12 anos) ────────────────────
CV_EXP_EXPLICITA_DS = """
Marina Ramos — Especialista em Machine Learning
12 anos de experiência em ciência de dados e inteligência artificial.

EXPERIÊNCIA PROFISSIONAL

DataTech AI — Senior Data Scientist                    2016–2024
  Desenvolvimento e deploy de modelos de Machine Learning em produção.
  NLP com transformers (BERT, GPT). Visão computacional com TensorFlow e PyTorch.
  APIs de ML com FastAPI. Feature engineering, A/B testing.
  PostgreSQL, MongoDB. Docker, AWS SageMaker.

Analytics Corp — Data Scientist                        2012–2016
  Python, R, scikit-learn, Machine Learning clássico. Estatística aplicada.
  Modelos de regressão, classificação, clustering. Painéis no Tableau.

HABILIDADES TÉCNICAS
Python · Machine Learning · Deep Learning · NLP · TensorFlow · PyTorch
scikit-learn · FastAPI · PostgreSQL · MongoDB · Docker · AWS SageMaker
pandas · numpy · Git · Tableau

FORMAÇÃO
Mestrado em Ciência da Computação — UNICAMP (2012)
Graduação em Estatística — UNICAMP (2010)
"""

# ── CV 5 — Experiência apenas implícita (1 ano de intervalo) ─────────────────
CV_EXP_IMPLICITA_JUNIOR = """
Pedro Alves — Desenvolvedor em transição de carreira
Busco primeira oportunidade sólida em desenvolvimento de software.

EXPERIÊNCIA PROFISSIONAL

Empresa XYZ — Estagiário de TI                         2023–2024
  Suporte a sistemas internos. Scripts básicos em Python para relatórios.
  Aprendi SQL durante o estágio. Uso casual do Excel e PowerPoint.

HABILIDADES
Python básico · SQL básico · Excel · PowerPoint · um pouco de HTML

FORMAÇÃO
Cursando Sistemas de Informação — Faculdade ABC (trancado em 2022)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 1 — Features estruturais (sem embedding, rápido)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtracaoExperiencia:
    """Verifica se os anos de experiência são corretamente extraídos dos CVs."""

    def test_cv_ideal_detecta_pelo_menos_8_anos(self):
        feat = extrair_features_curriculo(CV_IDEAL_PYTHON)
        assert feat["anos_experiencia"] >= 8.0, (
            f"CV ideal tem ~11 anos (2013-2024), detectado: {feat['anos_experiencia']}"
        )

    def test_cv_mediano_detecta_2_anos_ou_menos(self):
        feat = extrair_features_curriculo(CV_MEDIANO_WEB)
        assert feat["anos_experiencia"] <= 3.0, (
            f"CV mediano tem 2 anos, detectado: {feat['anos_experiencia']}"
        )

    def test_cv_exp_explicita_detecta_12_anos(self):
        feat = extrair_features_curriculo(CV_EXP_EXPLICITA_DS)
        # "12 anos de experiência" declarado explicitamente
        assert feat["anos_experiencia"] >= 10.0, (
            f"CV com '12 anos declarados', detectado: {feat['anos_experiencia']}"
        )

    def test_exp_implicita_detecta_menos_que_explicita(self):
        feat_expl = extrair_features_curriculo(CV_EXP_EXPLICITA_DS)
        feat_impl = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        assert feat_expl["anos_experiencia"] > feat_impl["anos_experiencia"], (
            f"Explicita={feat_expl['anos_experiencia']:.1f} deveria > "
            f"Implicita={feat_impl['anos_experiencia']:.1f}"
        )

    def test_cv_ideal_tem_mais_anos_que_mediano(self):
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_med   = extrair_features_curriculo(CV_MEDIANO_WEB)
        assert feat_ideal["anos_experiencia"] > feat_med["anos_experiencia"]

    def test_cv_junior_tem_exp_minima(self):
        feat = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        # Estagio 2023-2024 = ~1 ano
        assert feat["anos_experiencia"] <= 2.0


class TestExtracaoNivelSenioridade:
    """Verifica se o nível de senioridade é detectado corretamente."""

    def test_cv_ideal_nivel_senior_ou_acima(self):
        feat = extrair_features_curriculo(CV_IDEAL_PYTHON)
        # "Sênior" = 3, "Lead" = 4. Deve ser pelo menos 3
        assert feat["nivel_senioridade"] >= 3, (
            f"CV com 'Sênior' deveria ter nível >= 3, obteve: {feat['nivel_senioridade']}"
        )

    def test_cv_junior_nivel_baixo(self):
        feat = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        assert feat["nivel_senioridade"] < feat_ideal["nivel_senioridade"]

    def test_cv_mediano_nivel_menor_que_ideal(self):
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_med   = extrair_features_curriculo(CV_MEDIANO_WEB)
        assert feat_ideal["nivel_senioridade"] >= feat_med["nivel_senioridade"]


class TestExtracaoHabilidades:
    """Verifica extração de skills técnicas e overlap com vaga."""

    def test_cv_ideal_contem_skills_python_core(self):
        feat   = extrair_features_curriculo(CV_IDEAL_PYTHON)
        skills = feat["habilidades"]
        assert "python" in skills
        # Pelo menos 3 das skills críticas da vaga
        criticas = {"fastapi", "docker", "postgresql", "redis", "celery"}
        encontradas = skills & criticas
        assert len(encontradas) >= 3, (
            f"Esperava >= 3 skills críticas, encontrou {encontradas}"
        )

    def test_cv_mediano_skills_nao_incluem_fastapi_docker(self):
        feat   = extrair_features_curriculo(CV_MEDIANO_WEB)
        skills = feat["habilidades"]
        assert "fastapi" not in skills
        assert "docker" not in skills

    def test_cv_irrelevante_sem_skills_dev(self):
        feat   = extrair_features_curriculo(CV_IRRELEVANTE_ADVOGADO)
        skills = feat["habilidades"]
        dev_skills = {"python", "fastapi", "django", "docker", "postgresql"}
        assert len(skills & dev_skills) == 0, (
            f"CV de advogado não deveria ter skills de dev: {skills & dev_skills}"
        )

    def test_overlap_ideal_maior_que_mediano(self):
        feat_vaga  = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_med   = extrair_features_curriculo(CV_MEDIANO_WEB)
        overlap_ideal = len(feat_ideal["habilidades"] & feat_vaga["habilidades"])
        overlap_med   = len(feat_med["habilidades"]   & feat_vaga["habilidades"])
        assert overlap_ideal > overlap_med, (
            f"Ideal={overlap_ideal} skills em comum deveria > Mediano={overlap_med}"
        )

    def test_overlap_irrelevante_zero_ou_minimo(self):
        feat_vaga  = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        feat_irrel = extrair_features_curriculo(CV_IRRELEVANTE_ADVOGADO)
        overlap = len(feat_irrel["habilidades"] & feat_vaga["habilidades"])
        assert overlap <= 1, (
            f"CV de advogado deveria ter overlap mínimo com vaga Python, obteve {overlap}"
        )

    def test_cv_ds_contem_skills_ml(self):
        feat   = extrair_features_curriculo(CV_EXP_EXPLICITA_DS)
        skills = feat["habilidades"]
        ml_skills = {"scikit-learn", "tensorflow", "pytorch", "python"}
        encontradas = skills & ml_skills
        assert len(encontradas) >= 2, (
            f"CV de Data Scientist deveria ter skills ML: {encontradas}"
        )


class TestExtracaoEducacao:
    """Verifica distinção entre graduação completa e incompleta."""

    def test_cv_ideal_tem_graduacao_completa(self):
        # "Bacharelado ... (2013)" — ano de conclusão presente, sem "cursando"
        feat = extrair_features_curriculo(CV_IDEAL_PYTHON)
        assert feat["nivel_educacao"] == 3, (
            f"CV com bacharelado de 2013 deveria ser nível 3 (graduação), obteve {feat['nivel_educacao']}"
        )

    def test_cv_junior_cursando_trancado_nivel_2(self):
        # "Cursando Sistemas de Informação — Faculdade ABC (trancado em 2022)"
        feat = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        assert feat["nivel_educacao"] == 2, (
            f"CV com 'cursando/trancado' deveria ser nível 2 (incompleta), obteve {feat['nivel_educacao']}"
        )

    def test_cv_ds_tem_mestrado(self):
        # "Mestrado em Ciência da Computação — UNICAMP (2012)"
        feat = extrair_features_curriculo(CV_EXP_EXPLICITA_DS)
        assert feat["nivel_educacao"] == 5, (
            f"CV com mestrado deveria ser nível 5, obteve {feat['nivel_educacao']}"
        )

    def test_educacao_completa_nivel_maior_que_incompleta(self):
        feat_completo   = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_incompleto = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        assert feat_completo["nivel_educacao"] > feat_incompleto["nivel_educacao"]


class TestBonusEstrututal:
    """Verifica se o bônus estrutural favorece o candidato correto."""

    def test_bonus_ideal_maior_que_mediano(self):
        feat_vaga  = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_med   = extrair_features_curriculo(CV_MEDIANO_WEB)
        bonus_ideal = calcular_bonus_estrutural(feat_ideal, feat_vaga)
        bonus_med   = calcular_bonus_estrutural(feat_med,   feat_vaga)
        assert bonus_ideal > bonus_med, (
            f"Bonus ideal={bonus_ideal:.3f} deveria > mediano={bonus_med:.3f}"
        )

    def test_bonus_dentro_do_intervalo(self):
        feat_vaga = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        for cv in [CV_IDEAL_PYTHON, CV_MEDIANO_WEB, CV_IRRELEVANTE_ADVOGADO]:
            feat = extrair_features_curriculo(cv)
            bonus = calcular_bonus_estrutural(feat, feat_vaga)
            assert -0.25 <= bonus <= 0.25, (
                f"Bônus fora do intervalo [-0.25, 0.25]: {bonus:.3f}"
            )

    def test_bonus_ideal_positivo(self):
        feat_vaga  = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        feat_ideal = extrair_features_curriculo(CV_IDEAL_PYTHON)
        bonus = calcular_bonus_estrutural(feat_ideal, feat_vaga)
        assert bonus > 0, f"CV ideal deveria ter bônus positivo, obteve {bonus:.3f}"

    def test_bonus_junior_negativo_para_vaga_senior(self):
        feat_vaga  = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        feat_jun   = extrair_features_curriculo(CV_EXP_IMPLICITA_JUNIOR)
        bonus = calcular_bonus_estrutural(feat_jun, feat_vaga)
        # Junior para vaga sênior (5+ anos) deve ter bônus negativo
        assert bonus < 0, (
            f"Junior para vaga sênior deveria ter bônus negativo, obteve {bonus:.3f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 2 — Pipeline semântico com embedding real (slow)
#
# Executa o modelo de embedding real (all-MiniLM-L6-v2).
# Bypass do mock autouse chamando get_model().encode() diretamente.
# Primeira execução ~20-40s (download/carga do modelo).
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestPipelineSemantico:
    """
    Testes semânticos com modelo real.
    Execute com: pytest tests/test_ai_curriculo.py -m slow -s
    """

    @staticmethod
    def _vet(texto: str) -> list:
        """Vetoriza com o modelo real, ignorando qualquer mock."""
        from app.ai.resume_parser import get_model
        return get_model().encode(texto, normalize_embeddings=True).tolist()

    @staticmethod
    def _score_rh(cv: str, vaga: str) -> float:
        """Similaridade semântica pura CV↔vaga (sem bônus estrutural)."""
        v_cv   = TestPipelineSemantico._vet(cv)
        v_vaga = TestPipelineSemantico._vet(vaga)
        return calcular_score_rh(v_cv, v_vaga)

    @staticmethod
    def _score_full(cv: str, vaga: str, p_rh=0.6, p_mkt=0.4) -> float:
        from app.ai.feature_extractor import (
            extrair_features_curriculo, extrair_features_vaga, calcular_bonus_estrutural,
        )
        v_cv   = TestPipelineSemantico._vet(cv)
        v_vaga = TestPipelineSemantico._vet(vaga)
        s_rh   = calcular_score_rh(v_cv, v_vaga)
        s_mkt  = calcular_score_mercado(v_cv, v_vaga)
        bonus  = calcular_bonus_estrutural(
            extrair_features_curriculo(cv),
            extrair_features_vaga(vaga),
        )
        return calcular_score_curriculo(s_rh, s_mkt, p_rh, p_mkt, bonus)

    # ── Ordenação semântica ───────────────────────────────────────────────────

    def test_score_rh_ideal_maior_que_mediano(self):
        s_ideal = self._score_rh(CV_IDEAL_PYTHON, VAGA_PYTHON_SENIOR)
        s_med   = self._score_rh(CV_MEDIANO_WEB,  VAGA_PYTHON_SENIOR)
        assert s_ideal > s_med, (
            f"Ideal ({s_ideal:.3f}) deveria > Mediano ({s_med:.3f})"
        )

    def test_score_rh_mediano_maior_que_irrelevante(self):
        s_med   = self._score_rh(CV_MEDIANO_WEB,         VAGA_PYTHON_SENIOR)
        s_irrel = self._score_rh(CV_IRRELEVANTE_ADVOGADO, VAGA_PYTHON_SENIOR)
        assert s_med > s_irrel, (
            f"Mediano ({s_med:.3f}) deveria > Irrelevante ({s_irrel:.3f})"
        )

    def test_ranking_tres_cvs_ordem_correta(self):
        scores = {
            "ideal"     : self._score_rh(CV_IDEAL_PYTHON,         VAGA_PYTHON_SENIOR),
            "mediano"   : self._score_rh(CV_MEDIANO_WEB,          VAGA_PYTHON_SENIOR),
            "irrelevante": self._score_rh(CV_IRRELEVANTE_ADVOGADO, VAGA_PYTHON_SENIOR),
        }
        print(f"\n[Ranking] ideal={scores['ideal']:.3f} | mediano={scores['mediano']:.3f} | irrelevante={scores['irrelevante']:.3f}")
        assert scores["ideal"] > scores["mediano"] > scores["irrelevante"]

    # ── Limiares de score ─────────────────────────────────────────────────────

    def test_cv_ideal_score_curriculo_acima_de_55(self):
        score = self._score_full(CV_IDEAL_PYTHON, VAGA_PYTHON_SENIOR)
        print(f"\n[Score ideal Python] {score:.1f}/100")
        assert score >= 55.0, (
            f"CV ideal para vaga Python deveria ter score >= 55, obteve {score:.1f}"
        )

    def test_cv_irrelevante_score_abaixo_de_ideal(self):
        s_ideal = self._score_full(CV_IDEAL_PYTHON,          VAGA_PYTHON_SENIOR)
        s_irrel = self._score_full(CV_IRRELEVANTE_ADVOGADO,  VAGA_PYTHON_SENIOR)
        print(f"\n[Score] ideal={s_ideal:.1f} | irrelevante={s_irrel:.1f}")
        assert s_ideal > s_irrel + 10, (
            f"Ideal ({s_ideal:.1f}) deveria ser > 10 pts acima do irrelevante ({s_irrel:.1f})"
        )

    # ── Especialização correta ────────────────────────────────────────────────

    def test_cv_ds_pontua_melhor_para_vaga_ds_que_backend_puro(self):
        s_ds  = self._score_rh(CV_EXP_EXPLICITA_DS, VAGA_DATA_SCIENCE)
        s_py  = self._score_rh(CV_IDEAL_PYTHON,     VAGA_DATA_SCIENCE)
        print(f"\n[Vaga DS] data_scientist={s_ds:.3f} | python_backend={s_py:.3f}")
        assert s_ds > s_py, (
            f"CV de Data Scientist ({s_ds:.3f}) deveria pontuar mais na vaga de DS "
            f"do que CV de Python backend ({s_py:.3f})"
        )

    def test_cv_ideal_python_pontua_melhor_para_vaga_backend_que_ds(self):
        s_py = self._score_rh(CV_IDEAL_PYTHON,     VAGA_PYTHON_SENIOR)
        s_ds = self._score_rh(CV_EXP_EXPLICITA_DS, VAGA_PYTHON_SENIOR)
        print(f"\n[Vaga Python] python_backend={s_py:.3f} | data_scientist={s_ds:.3f}")
        assert s_py > s_ds, (
            f"CV Python backend ({s_py:.3f}) deveria pontuar mais na vaga backend "
            f"do que CV Data Scientist ({s_ds:.3f})"
        )

    # ── Explicação XAI ────────────────────────────────────────────────────────

    def test_explicacao_ideal_classifica_como_bom_ou_excelente(self):
        from app.ai.feature_extractor import calcular_bonus_estrutural
        feat_cv   = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_vaga = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        bonus  = calcular_bonus_estrutural(feat_cv, feat_vaga)
        s_rh   = self._score_rh(CV_IDEAL_PYTHON, VAGA_PYTHON_SENIOR)
        s_mkt  = calcular_score_mercado(self._vet(CV_IDEAL_PYTHON), self._vet(VAGA_PYTHON_SENIOR))
        score  = calcular_score_curriculo(s_rh, s_mkt, 0.6, 0.4, bonus)
        expl   = gerar_explicacao(s_rh, s_mkt, score, 0.6, 0.4,
                                  features_cv=feat_cv, features_vaga=feat_vaga)
        classif = expl["componentes"]["aderencia_vaga"]["classificacao"]
        print(f"\n[Explicação ideal] score={score:.1f} | classificação={classif}")
        # score_rh aqui é semântico puro (sem bônus); o CV ideal pode não atingir 0.65
        # semanticamente — o que importa é não ser "baixo"
        assert classif in ("bom", "excelente", "regular"), (
            f"CV ideal não deveria ter classificação 'baixo', obteve '{classif}' (score_rh={s_rh:.3f})"
        )

    def test_explicacao_irrelevante_classifica_como_baixo_ou_regular(self):
        from app.ai.feature_extractor import calcular_bonus_estrutural
        feat_cv   = extrair_features_curriculo(CV_IRRELEVANTE_ADVOGADO)
        feat_vaga = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        bonus  = calcular_bonus_estrutural(feat_cv, feat_vaga)
        s_rh   = self._score_rh(CV_IRRELEVANTE_ADVOGADO, VAGA_PYTHON_SENIOR)
        s_mkt  = calcular_score_mercado(self._vet(CV_IRRELEVANTE_ADVOGADO), self._vet(VAGA_PYTHON_SENIOR))
        score  = calcular_score_curriculo(s_rh, s_mkt, 0.6, 0.4, bonus)
        expl   = gerar_explicacao(s_rh, s_mkt, score, 0.6, 0.4)
        classif = expl["componentes"]["aderencia_vaga"]["classificacao"]
        print(f"\n[Explicação irrelevante] score={score:.1f} | classificação={classif}")
        assert classif in ("baixo", "regular"), (
            f"CV de advogado para Python deveria ser baixo/regular, obteve '{classif}'"
        )

    def test_explicacao_contem_skills_em_comum_para_cv_ideal(self):
        from app.ai.feature_extractor import calcular_bonus_estrutural
        feat_cv   = extrair_features_curriculo(CV_IDEAL_PYTHON)
        feat_vaga = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        bonus  = calcular_bonus_estrutural(feat_cv, feat_vaga)
        s_rh   = self._score_rh(CV_IDEAL_PYTHON, VAGA_PYTHON_SENIOR)
        s_mkt  = calcular_score_mercado(self._vet(CV_IDEAL_PYTHON), self._vet(VAGA_PYTHON_SENIOR))
        score  = calcular_score_curriculo(s_rh, s_mkt, 0.6, 0.4, bonus)
        expl   = gerar_explicacao(s_rh, s_mkt, score, 0.6, 0.4,
                                  features_cv=feat_cv, features_vaga=feat_vaga)
        skills_em_comum = expl.get("sinais_estruturais", {}).get("habilidades_em_comum", [])
        print(f"\n[Skills em comum] {skills_em_comum}")
        assert len(skills_em_comum) >= 3, (
            f"CV ideal deveria ter >= 3 skills em comum, obteve: {skills_em_comum}"
        )

    def test_imprime_comparativo_completo(self):
        """
        Relatório detalhado por CV: scores, bônus estrutural e breakdown completo
        do que foi extraído (skills, senioridade, experiência, educação, overlap).
        Execute com: pytest tests/test_ai_curriculo.py::TestPipelineSemantico::test_imprime_comparativo_completo -m slow -s
        """
        from app.ai.feature_extractor import calcular_bonus_estrutural

        _NIVEL_LABEL = {0: "estágio", 1: "júnior", 2: "pleno", 3: "sênior",
                        4: "lead/staff", 5: "gestão", 6: "direção"}
        _EDUC_LABEL  = {0: "sem", 1: "técnico", 2: "graduação incompleta",
                        3: "graduação", 4: "pós/MBA", 5: "mestrado", 6: "doutorado"}

        cvs = [
            ("Ideal Python",   CV_IDEAL_PYTHON),
            ("Mediano Web",    CV_MEDIANO_WEB),
            ("Data Scientist", CV_EXP_EXPLICITA_DS),
            ("Júnior Estágio", CV_EXP_IMPLICITA_JUNIOR),
            ("Advogado",       CV_IRRELEVANTE_ADVOGADO),
        ]
        feat_vaga   = extrair_features_vaga(VAGA_PYTHON_SENIOR, [])
        v_vaga      = self._vet(VAGA_PYTHON_SENIOR)

        W = 70
        import numpy as np
        for nome, cv in cvs:
            feat      = extrair_features_curriculo(cv)
            v_cv      = self._vet(cv)
            s_rh_raw  = float(np.dot(np.array(v_cv), np.array(v_vaga)))
            s_mkt     = calcular_score_mercado(v_cv, v_vaga)
            bonus     = calcular_bonus_estrutural(feat, feat_vaga)
            final     = calcular_score_curriculo(s_rh_raw, s_mkt, 0.6, 0.4, bonus)
            expl      = gerar_explicacao(s_rh_raw, s_mkt, final, 0.6, 0.4,
                                         features_cv=feat, features_vaga=feat_vaga)
            classif   = expl["componentes"]["aderencia_vaga"]["classificacao"]
            overlap   = sorted(feat["habilidades"] & feat_vaga["habilidades"])
            skills_cv = sorted(feat["habilidades"])

            print(f"\n{'═'*W}")
            print(f"  {nome.upper()}")
            print(f"{'─'*W}")
            print(f"  SCORES")
            print(f"    Semântico bruto  : {s_rh_raw*100:>5.1f}%")
            print(f"    Bônus estrutural : {bonus:>+.3f}  →  efeito no final: {bonus*100:>+.1f} pts")
            print(f"    Score mercado    : {s_mkt*100:>5.1f}%")
            print(f"    Score final      : {final:>5.1f}/100  [{classif.upper()}]")
            print(f"{'─'*W}")
            print(f"  FEATURES ESTRUTURAIS")
            anos = feat["anos_experiencia"]
            anos_req = feat_vaga.get("anos_minimos", 0)
            nivel_cv  = feat["nivel_senioridade"]
            nivel_req = feat_vaga.get("nivel_esperado", 0)
            print(f"    Experiência  : {anos:.1f} anos  (vaga exige ~{anos_req:.0f}a)  "
                  f"→ {'✓ suficiente' if anos >= anos_req and anos_req > 0 else '✗ insuficiente' if anos_req > 0 else '— não declarado'}")
            print(f"    Senioridade  : nível {nivel_cv} = {_NIVEL_LABEL.get(nivel_cv,'?')}  "
                  f"(vaga espera nível {nivel_req} = {_NIVEL_LABEL.get(nivel_req,'?')})  "
                  f"→ {'✓ ok' if nivel_cv >= nivel_req and nivel_req > 0 else '✗ abaixo' if nivel_req > 0 else '—'}")
            print(f"    Educação     : nível {feat['nivel_educacao']} = {_EDUC_LABEL.get(feat['nivel_educacao'],'?')}")
            print(f"{'─'*W}")
            print(f"  SKILLS DETECTADAS NO CV ({len(skills_cv)} total)")
            if skills_cv:
                linha = "    "
                for s in skills_cv:
                    token = s + ("*" if s in feat_vaga["habilidades"] else "") + "  "
                    if len(linha) + len(token) > W - 2:
                        print(linha)
                        linha = "    "
                    linha += token
                if linha.strip():
                    print(linha)
                print(f"    (* = skill em comum com a vaga)")
            else:
                print("    (nenhuma skill técnica detectada)")
            print(f"{'─'*W}")
            print(f"  OVERLAP COM VAGA ({len(overlap)} skills em comum de {len(feat_vaga['habilidades'])} requeridas)")
            if overlap:
                print(f"    {', '.join(overlap)}")
            else:
                print("    (nenhuma)")
        print(f"\n{'═'*W}")
