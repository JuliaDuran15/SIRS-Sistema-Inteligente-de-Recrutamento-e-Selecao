"""Testes do extrator de features estruturadas de currículos."""
from datetime import datetime
import pytest
from app.ai.feature_extractor import (
    extrair_features_curriculo,
    extrair_features_vaga,
    calcular_bonus_estrutural,
    _extrair_anos_curriculo,
    _extrair_nivel,
    _extrair_habilidades,
    _extrair_educacao,
    _somar_intervalos_sem_sobreposicao,
)

ANO_ATUAL = datetime.now().year


class TestSomarIntervalos:
    def test_sem_sobreposicao(self):
        assert _somar_intervalos_sem_sobreposicao([(2015, 2018), (2019, 2022)]) == 6.0

    def test_com_sobreposicao(self):
        # 2015-2018 e 2017-2021 → merged 2015-2021 = 6
        assert _somar_intervalos_sem_sobreposicao([(2015, 2018), (2017, 2021)]) == 6.0

    def test_adjacentes_sao_mergeados(self):
        assert _somar_intervalos_sem_sobreposicao([(2015, 2018), (2018, 2022)]) == 7.0

    def test_tres_periodos_sem_sobreposicao(self):
        assert _somar_intervalos_sem_sobreposicao([(2010, 2013), (2014, 2018), (2018, 2022)]) == 11.0

    def test_lista_vazia(self):
        assert _somar_intervalos_sem_sobreposicao([]) == 0.0


class TestExtracaoAnos:
    def test_declaracao_explicita_prevalece(self):
        assert _extrair_anos_curriculo("10 anos de experiência em Python") == 10.0

    def test_padrao_experiencia_de_n_anos(self):
        assert _extrair_anos_curriculo("Experiência de 7 anos na área") == 7.0

    def test_padrao_mercado(self):
        assert _extrair_anos_curriculo("8 anos de mercado financeiro") == 8.0

    def test_multiplos_explicitos_usa_maior(self):
        texto = "2 anos de experiência em frontend, 8 anos de experiência total"
        assert _extrair_anos_curriculo(texto) == 8.0

    def test_intervalos_simples(self):
        # 2018–2022 = 4 anos; 2022–2024 = 2 anos → total 6
        texto = "Empresa X (2018-2022). Empresa Y (2022-2024). Python, Docker."
        assert _extrair_anos_curriculo(texto) == pytest.approx(6.0, abs=0.5)

    def test_intervalos_com_sobreposicao(self):
        # 2015-2019 e 2017-2022 → merged 2015-2022 = 7 (não 9)
        texto = "Emprego A: 2015-2019. Emprego B: 2017-2022."
        resultado = _extrair_anos_curriculo(texto)
        assert resultado == pytest.approx(7.0, abs=0.5)

    def test_intervalo_ate_presente(self):
        # 2020 - atual = anos_atual - 2020
        texto = "Empresa atual: 2020 - presente. Python, AWS."
        resultado = _extrair_anos_curriculo(texto)
        esperado = ANO_ATUAL - 2020
        assert resultado == pytest.approx(esperado, abs=1.0)

    def test_multiplos_intervalos_sem_sobreposicao(self):
        # 2013–2016 (3) + 2016–2019 (3) + 2019–2023 (4) = 10
        texto = (
            "Empresa A: 2013-2016. Analista Pleno.\n"
            "Empresa B: 2016-2019. Analista Sênior.\n"
            "Empresa C: 2019-2023. Tech Lead."
        )
        resultado = _extrair_anos_curriculo(texto)
        assert resultado == pytest.approx(10.0, abs=1.0)

    def test_sem_data_retorna_zero(self):
        assert _extrair_anos_curriculo("Desenvolvedor com habilidades em Python e SQL") == 0.0

    def test_limite_superior_ignorado(self):
        # 99 anos é implausível — deve ser ignorado
        assert _extrair_anos_curriculo("99 anos de experiência") == 0.0

    def test_desde_ano_detectado_como_intervalo(self):
        # "desde 2015" → intervalo aberto 2015-atual
        texto = "Trabalhou em tecnologia desde 2015. Python, Django, PostgreSQL."
        resultado = _extrair_anos_curriculo(texto)
        esperado = ANO_ATUAL - 2015
        assert resultado == pytest.approx(esperado, abs=1.0)

    def test_fallback_conservador(self):
        # Anos soltos sem padrão de intervalo → fallback divide por 1.4
        # "entre X e Y" não é detectado como intervalo (usa " e ", não "-")
        texto = "Trabalhou em duas empresas, entre 2012 e 2024, acumulando experiência em Python."
        resultado = _extrair_anos_curriculo(texto)
        span_puro = ANO_ATUAL - 2012
        assert resultado < span_puro   # conservador: menor que span bruto
        assert resultado > 0


class TestExtracaoNivel:
    def test_senior(self):
        assert _extrair_nivel("Desenvolvedor Python Sênior com 8 anos") == 3

    def test_junior(self):
        assert _extrair_nivel("Desenvolvedor Júnior buscando oportunidade") == 1

    def test_pleno(self):
        assert _extrair_nivel("Cargo: Analista Pleno") == 2

    def test_tech_lead(self):
        assert _extrair_nivel("Tech Lead responsável por equipe de 5") == 4

    def test_sem_nivel_retorna_zero(self):
        assert _extrair_nivel("Desenvolvedor com experiência em Django") == 0

    def test_prioriza_maior_nivel(self):
        assert _extrair_nivel("Avançou de júnior para sênior em 3 anos") == 3

    def test_case_insensitive(self):
        assert _extrair_nivel("DESENVOLVEDOR SÊNIOR") == 3

    def test_estagiario(self):
        assert _extrair_nivel("Estagiário em Ciência da Computação") == 0

    def test_gerente(self):
        assert _extrair_nivel("Gerente de Engenharia — responsável por 3 squads") == 5


class TestExtracaoHabilidades:
    def test_python(self):
        assert "python" in _extrair_habilidades("Desenvolvedor Python FastAPI")

    def test_fastapi(self):
        assert "fastapi" in _extrair_habilidades("API REST com FastAPI e Docker")

    def test_node_com_ponto(self):
        assert "node.js" in _extrair_habilidades("Backend em Node.js e TypeScript")

    def test_multiplas_skills(self):
        habs = _extrair_habilidades("Python, Docker, Kubernetes, PostgreSQL, Redis")
        assert {"python", "docker", "kubernetes", "postgresql", "redis"}.issubset(habs)

    def test_sem_habilidades_conhecidas(self):
        assert len(_extrair_habilidades("Experiência em gestão de pessoas")) == 0

    def test_nao_captura_substrings(self):
        # "r" não deve ser capturado dentro de "arquitetura"
        habs = _extrair_habilidades("arquitetura de microsserviços")
        assert "r" not in habs

    def test_case_insensitive(self):
        assert "python" in _extrair_habilidades("PYTHON, DOCKER")


class TestExtracaoEducacao:
    def test_graduacao_via_formacao(self):
        formacao = [{"nivel": "graduacao", "curso": "CC", "instituicao": "USP", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 2

    def test_mba_via_formacao(self):
        formacao = [{"nivel": "mba", "curso": "MBA RH", "instituicao": "FGV", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 3

    def test_mestrado_via_formacao(self):
        formacao = [{"nivel": "mestrado", "curso": "MSc", "instituicao": "USP", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 4

    def test_maior_nivel_entre_formacoes(self):
        formacao = [
            {"nivel": "graduacao", "curso": "CC", "instituicao": "USP", "status": "concluido"},
            {"nivel": "mestrado",  "curso": "MSc", "instituicao": "USP", "status": "concluido"},
        ]
        assert _extrair_educacao("", formacao) == 4

    def test_fallback_via_texto(self):
        assert _extrair_educacao("Possui mestrado em engenharia", []) == 4

    def test_sem_educacao(self):
        assert _extrair_educacao("Experiência em Python", []) == 0


class TestBonusEstrutural:
    def test_candidato_perfeito_bonus_alto(self):
        feat_cv = {
            "anos_experiencia" : 8.0,
            "nivel_senioridade": 3,
            "habilidades"      : {"python", "fastapi", "postgresql", "docker"},
        }
        feat_vaga = {
            "anos_minimos"  : 5.0,
            "nivel_esperado": 3,
            "habilidades"   : {"python", "fastapi", "postgresql", "docker"},
        }
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) > 0.10

    def test_candidato_aquem_penalidade(self):
        feat_cv = {
            "anos_experiencia" : 1.0,
            "nivel_senioridade": 1,
            "habilidades"      : {"python"},
        }
        feat_vaga = {
            "anos_minimos"  : 8.0,
            "nivel_esperado": 3,
            "habilidades"   : {"python", "fastapi", "postgresql", "docker", "kubernetes"},
        }
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) < -0.05

    def test_bonus_maximo_015(self):
        feat_cv   = {"anos_experiencia": 30.0, "nivel_senioridade": 6,
                     "habilidades": {"python", "fastapi", "postgresql", "docker",
                                     "kubernetes", "redis", "aws"}}
        feat_vaga = {"anos_minimos": 1.0, "nivel_esperado": 1,
                     "habilidades": {"python", "fastapi"}}
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) <= 0.15

    def test_penalidade_minima_menos_015(self):
        feat_cv   = {"anos_experiencia": 0.0, "nivel_senioridade": 0, "habilidades": set()}
        feat_vaga = {"anos_minimos": 15.0, "nivel_esperado": 6,
                     "habilidades": {"python", "aws", "kubernetes", "kafka"}}
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) >= -0.15

    def test_sem_requisitos_retorna_zero(self):
        feat_cv   = {"anos_experiencia": 5.0, "nivel_senioridade": 2, "habilidades": {"python"}}
        feat_vaga = {"anos_minimos": 0.0, "nivel_esperado": 0, "habilidades": set()}
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) == 0.0

    def test_mais_skills_mais_bonus(self):
        base = {"anos_experiencia": 0, "nivel_senioridade": 0}
        vaga = {"anos_minimos": 0, "nivel_esperado": 0,
                "habilidades": {"python", "docker", "postgresql"}}
        b0 = calcular_bonus_estrutural({**base, "habilidades": set()}, vaga)
        b3 = calcular_bonus_estrutural({**base, "habilidades": {"python", "docker", "postgresql"}}, vaga)
        assert b3 > b0

    def test_nivel_inferido_do_senioridade_quando_sem_anos(self):
        # Vaga sem anos mínimos explícitos mas com nível sênior (3)
        # → inferido como 6 anos mínimos
        feat_cv   = {"anos_experiencia": 8.0, "nivel_senioridade": 3, "habilidades": set()}
        feat_vaga = {"anos_minimos": 0.0, "nivel_esperado": 3, "habilidades": set()}
        bonus = calcular_bonus_estrutural(feat_cv, feat_vaga)
        # 8 >= 6 (inferido) → bônus de experiência positivo
        assert bonus > 0


class TestExtrairFeaturesCompleto:
    def test_curriculo_senior_explora_intervalos(self):
        texto = (
            "Desenvolvedora Python Sênior.\n"
            "Empresa A: 2015-2019. Backend Python.\n"
            "Empresa B: 2019-2023. FastAPI, PostgreSQL, Docker.\n"
            "Empresa C: 2023-presente. Tech Lead AWS."
        )
        formacao = [{"nivel": "graduacao", "curso": "CC",
                     "instituicao": "USP", "status": "concluido"}]
        feat = extrair_features_curriculo(texto, formacao)

        assert feat["anos_experiencia"] >= 8.0   # pelo menos 8 anos (2015→atual)
        assert feat["nivel_senioridade"] >= 3    # sênior ou tech lead
        assert "python" in feat["habilidades"]
        assert "fastapi" in feat["habilidades"]
        assert feat["nivel_educacao"] == 2

    def test_vaga_com_termos_mercado_enriquece_habilidades(self):
        texto_vaga = (
            "Buscamos desenvolvedor Python Sênior com 5 anos de experiência. "
            "FastAPI e PostgreSQL obrigatórios. AWS é diferencial."
        )
        termos = [{"termo": "kubernetes", "frequencia": 50},
                  {"termo": "microservices", "frequencia": 30}]
        feat = extrair_features_vaga(texto_vaga, termos)

        assert feat["anos_minimos"] == 5.0
        assert feat["nivel_esperado"] == 3
        assert "python" in feat["habilidades"]
        assert "kubernetes" in feat["habilidades"]
        assert "microservices" in feat["habilidades"]

    def test_cv_junior_vs_vaga_senior_penalidade(self):
        cv = (
            "Desenvolvedor júnior com 1 ano de experiência. "
            "2023-presente. Python básico, HTML."
        )
        vaga = (
            "Buscamos desenvolvedor Python Sênior com 5 anos de experiência. "
            "FastAPI, Docker, PostgreSQL, AWS, Kubernetes obrigatórios."
        )
        feat_cv   = extrair_features_curriculo(cv)
        feat_vaga = extrair_features_vaga(vaga)
        bonus     = calcular_bonus_estrutural(feat_cv, feat_vaga)
        assert bonus < 0, "Júnior vs Sênior deve ter penalidade estrutural"
