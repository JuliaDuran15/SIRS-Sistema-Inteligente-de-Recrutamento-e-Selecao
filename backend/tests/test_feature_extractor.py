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
    _extrair_proficiencia,
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


class TestExtracao_Secao_vs_TextoCompleto:
    """
    Verifica que a extração de intervalos usa a seção 'experiência' quando
    disponível, evitando contar anos de formação ou outras seções.
    """

    def test_anos_formacao_nao_contam_quando_secao_detectada(self):
        """
        CV com cabeçalho 'FORMAÇÃO' e 'EXPERIÊNCIA PROFISSIONAL' bem definidos.
        O ano de conclusão da faculdade (2010) não deve inflar o total.
        """
        texto = (
            "EXPERIÊNCIA PROFISSIONAL\n"
            "Empresa Alpha: 2018-2024. Desenvolvedor Python Sênior.\n"
            "\n"
            "FORMAÇÃO\n"
            "Ciência da Computação — USP (2006-2010).\n"
        )
        resultado = _extrair_anos_curriculo(texto)
        # Deve contar só 2018-2024 = 6 anos, não misturar com 2006-2010
        assert resultado == pytest.approx(6.0, abs=0.5), (
            f"Com seção detectada, deveria contar só exp. profissional (6a), obteve {resultado}"
        )

    def test_sem_cabecalho_usa_texto_completo(self):
        """
        CV sem cabeçalhos de seção → fallback para texto completo.
        Neste caso o comportamento anterior é mantido.
        """
        texto = (
            "João Silva, desenvolvedor Python. "
            "Trabalhou na Empresa X de 2019 a 2023. "
            "Formado em CC em 2015."
        )
        resultado = _extrair_anos_curriculo(texto)
        # Sem seção detectada: soma todos os intervalos encontrados
        assert resultado > 0

    def test_formacao_dentro_da_secao_experiencia_ainda_conta(self):
        """
        [LIMITAÇÃO CONHECIDA] Se a formação está dentro da seção experiência
        (CV mal estruturado), ainda é contada.
        """
        texto = (
            "EXPERIÊNCIA\n"
            "Empresa A: 2018-2022. Dev Python.\n"
            "Mestrado USP: 2014-2016.\n"
        )
        resultado = _extrair_anos_curriculo(texto)
        # Ambos os intervalos estão na seção experiência → ambos contam
        assert resultado >= 4.0


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
    def test_graduacao_concluida_via_formacao(self):
        formacao = [{"nivel": "graduacao", "curso": "CC", "instituicao": "USP", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 3

    def test_graduacao_cursando_via_formacao(self):
        formacao = [{"nivel": "graduacao", "curso": "CC", "instituicao": "ABC", "status": "cursando"}]
        assert _extrair_educacao("", formacao) == 2

    def test_graduacao_trancada_via_formacao(self):
        formacao = [{"nivel": "graduacao", "curso": "SI", "instituicao": "XYZ", "status": "trancado"}]
        assert _extrair_educacao("", formacao) == 2

    def test_mba_via_formacao(self):
        formacao = [{"nivel": "mba", "curso": "MBA RH", "instituicao": "FGV", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 4

    def test_mestrado_via_formacao(self):
        formacao = [{"nivel": "mestrado", "curso": "MSc", "instituicao": "USP", "status": "concluido"}]
        assert _extrair_educacao("", formacao) == 5

    def test_maior_nivel_entre_formacoes(self):
        formacao = [
            {"nivel": "graduacao", "curso": "CC", "instituicao": "USP", "status": "concluido"},
            {"nivel": "mestrado",  "curso": "MSc", "instituicao": "USP", "status": "concluido"},
        ]
        assert _extrair_educacao("", formacao) == 5

    def test_fallback_via_texto_mestrado(self):
        assert _extrair_educacao("Possui mestrado em engenharia", []) == 5

    def test_fallback_via_texto_graduacao_completa(self):
        assert _extrair_educacao("Bacharelado em Ciência da Computação — USP (2013)", []) == 3

    def test_fallback_via_texto_cursando(self):
        assert _extrair_educacao("Cursando Sistemas de Informação", []) == 2

    def test_fallback_via_texto_trancado(self):
        assert _extrair_educacao("Graduação trancada em 2021", []) == 2

    def test_mestrado_com_cursando_nao_rebaixa(self):
        # "cursando" não deve rebaixar mestrado — o rebaixe é só para graduação
        assert _extrair_educacao("Mestrado em andamento — UNICAMP", []) == 5

    def test_sem_educacao(self):
        assert _extrair_educacao("Experiência em Python", []) == 0


class TestProficiencia:
    """
    Verifica _extrair_proficiencia e seu efeito no bônus estrutural.

    Pesos: básico = 0.3 | padrão = 1.0 | avançado = 1.3
    A janela de detecção é ±70 chars em volta da menção da skill.
    """

    def test_sem_modificador_retorna_peso_padrao(self):
        feat = extrair_features_curriculo("Experiência com Python e Docker.")
        profic = feat["proficiencia_skills"]
        assert profic.get("python") == 1.0, (
            f"Sem modificador → peso padrão 1.0, obteve {profic.get('python')}"
        )

    def test_basico_retorna_0_3(self):
        feat = extrair_features_curriculo("Python básico para scripts simples.")
        profic = feat["proficiencia_skills"]
        assert profic.get("python") == 0.3, (
            f"'Python básico' → 0.3, obteve {profic.get('python')}"
        )

    def test_avancado_retorna_1_3(self):
        feat = extrair_features_curriculo("Python avançado — 8 anos de uso em produção.")
        profic = feat["proficiencia_skills"]
        assert profic.get("python") == 1.3, (
            f"'Python avançado' → 1.3, obteve {profic.get('python')}"
        )

    def test_iniciante_retorna_0_3(self):
        feat = extrair_features_curriculo("Docker: iniciante, ainda aprendendo.")
        profic = feat["proficiencia_skills"]
        assert profic.get("docker") == 0.3, (
            f"'Docker: iniciante' → 0.3, obteve {profic.get('docker')}"
        )

    def test_dominio_retorna_1_3(self):
        feat = extrair_features_curriculo("Domínio completo de Kubernetes em ambientes enterprise.")
        profic = feat["proficiencia_skills"]
        assert profic.get("kubernetes") == 1.3, (
            f"'Domínio de Kubernetes' → 1.3, obteve {profic.get('kubernetes')}"
        )

    def test_multiplas_skills_com_modificadores_distintos(self):
        # Skills separadas por > 70 chars para evitar sangramento da janela de detecção
        sep = " " * 80
        texto = f"Python avançado na empresa.{sep}Docker básico ainda aprendendo.{sep}PostgreSQL no dia-a-dia"
        profic = _extrair_proficiencia(texto.lower(), {"python", "docker", "postgresql"})
        assert profic["python"]     == 1.3, f"python avançado → 1.3, got {profic['python']}"
        assert profic["docker"]     == 0.3, f"docker básico → 0.3, got {profic['docker']}"
        assert profic["postgresql"] == 1.0, f"postgresql sem mod → 1.0, got {profic['postgresql']}"

    def test_noções_retorna_0_3(self):
        feat = extrair_features_curriculo("Noções de AWS e serviços de nuvem.")
        profic = feat["proficiencia_skills"]
        assert profic.get("aws") == 0.3, (
            f"'Noções de AWS' → 0.3, obteve {profic.get('aws')}"
        )

    def test_sólido_retorna_1_3(self):
        feat = extrair_features_curriculo("Sólido conhecimento em React e TypeScript.")
        profic = feat["proficiencia_skills"]
        assert profic.get("react") == 1.3, (
            f"'Sólido conhecimento em React' → 1.3, obteve {profic.get('react')}"
        )

    def test_modificador_fora_da_janela_nao_conta(self):
        # "básico" aparece longe demais da skill (> 70 chars)
        prefixo_longo = "x" * 80
        texto = f"Python. {prefixo_longo} básico em outras coisas."
        profic = _extrair_proficiencia(texto.lower(), {"python"})
        assert profic["python"] == 1.0, (
            f"Modificador fora da janela de 70 chars não deve afetar — obteve {profic['python']}"
        )

    # ── Efeito no bônus estrutural ────────────────────────────────────────────

    def test_skills_avancadas_dao_bonus_maior_que_basicas(self):
        vaga = {"anos_minimos": 0.0, "nivel_esperado": 0,
                "habilidades": {"python", "docker"}}

        feat_avancado = extrair_features_curriculo(
            "Python avançado para sistemas críticos. Docker avançado em produção."
        )
        feat_basico = extrair_features_curriculo(
            "Python básico para automação. Docker básico, ainda aprendendo."
        )
        bonus_av  = calcular_bonus_estrutural(feat_avancado, vaga)
        bonus_bas = calcular_bonus_estrutural(feat_basico,   vaga)
        assert bonus_av > bonus_bas, (
            f"Skills avançadas ({bonus_av:.3f}) devem dar bônus maior "
            f"que básicas ({bonus_bas:.3f}) para o mesmo overlap"
        )

    def test_bonus_basico_ainda_positivo_com_overlap_total(self):
        # Mesmo básico, se tem todas as skills → bônus positivo (não zero)
        vaga = {"anos_minimos": 0.0, "nivel_esperado": 0,
                "habilidades": {"python"}}
        feat = extrair_features_curriculo("Python básico para scripts.")
        bonus = calcular_bonus_estrutural(feat, vaga)
        assert bonus > 0, (
            f"Candidato com Python básico e overlap 100% deve ter bônus > 0, "
            f"obteve {bonus:.3f}"
        )

    def test_zero_overlap_penalidade_independe_de_proficiencia(self):
        # Mesmo que o candidato tenha skills avançadas, se nenhuma bate com a vaga → -0.15
        vaga = {"anos_minimos": 0.0, "nivel_esperado": 0,
                "habilidades": {"java", "springboot", "oracle"}}
        feat = extrair_features_curriculo(
            "Python avançado, React avançado, AWS avançado."
        )
        bonus = calcular_bonus_estrutural(feat, vaga)
        assert bonus <= -0.15, (
            f"Zero overlap deve dar penalidade de -0.15 (cap), "
            f"independente de proficiência — obteve {bonus:.3f}"
        )

    def test_peso_proficiencia_aparece_em_extrair_features_curriculo(self):
        # Skills separadas para evitar sangramento entre janelas de ±70 chars
        sep = " " * 80
        texto = f"Python avançado há 8 anos{sep}Docker básico recentemente{sep}PostgreSQL sem modificador aqui"
        feat = extrair_features_curriculo(texto)
        profic = feat["proficiencia_skills"]
        assert "python"     in profic, "python deve ter proficiência registrada"
        assert "docker"     in profic, "docker deve ter proficiência registrada"
        assert "postgresql" in profic, "postgresql deve ter proficiência registrada"
        assert profic["python"]     == 1.3, f"python avançado → 1.3, got {profic['python']}"
        assert profic["docker"]     == 0.3, f"docker básico → 0.3, got {profic['docker']}"
        assert profic["postgresql"] == 1.0, f"postgresql neutro → 1.0, got {profic['postgresql']}"

    def test_relatorio_proficiencia(self):
        """
        Imprime como a proficiência é detectada e como afeta o bônus estrutural.
        Execute com:
          pytest tests/test_feature_extractor.py::TestProficiencia::test_relatorio_proficiencia -s
        """
        W = 68

        # ── Casos de detecção de modificador ────────────────────────────────
        casos = [
            ("Python básico para scripts",            "python", "básico    → 0.3"),
            ("Python avançado, 8 anos em produção",   "python", "avançado  → 1.3"),
            ("Python no dia-a-dia",                   "python", "sem mod   → 1.0"),
            ("Noções de AWS e cloud",                 "aws",    "noções    → 0.3"),
            ("Domínio completo de Kubernetes",        "kubernetes", "domínio → 1.3"),
            ("Docker: iniciante, aprendendo",         "docker", "iniciante → 0.3"),
            ("Sólido conhecimento em React",          "react",  "sólido    → 1.3"),
            ("Expert em PostgreSQL há 5 anos",        "postgresql", "expert → 1.3"),
        ]

        print(f"\n{'═'*W}")
        print(f"  DETECÇÃO DE MODIFICADORES DE PROFICIÊNCIA")
        print(f"  Fonte → feature_extractor._extrair_proficiencia()")
        print(f"  Janela de busca: ±70 chars em volta da skill")
        print(f"{'─'*W}")
        print(f"  {'TEXTO':<42} {'SKILL':<12} {'PESO':<6}  {'ESPERADO'}")
        print(f"{'─'*W}")

        for texto, skill, esperado in casos:
            feat   = extrair_features_curriculo(texto)
            profic = feat["proficiencia_skills"]
            peso   = profic.get(skill, "não detectado")
            ok     = "✓" if peso != "não detectado" else "✗"
            print(f"  {ok} {texto:<41} {skill:<12} {str(peso):<6}  ({esperado})")

        # ── Efeito no bônus quando proficiência varia ────────────────────────
        print(f"\n{'═'*W}")
        print(f"  EFEITO DA PROFICIÊNCIA NO BÔNUS ESTRUTURAL")
        print(f"  Fonte → feature_extractor.calcular_bonus_estrutural()")
        print(f"  Cenário: vaga pede Python + Docker (2 skills, sem req de anos/nível)")
        print(f"{'─'*W}")

        vaga = {"anos_minimos": 0.0, "nivel_esperado": 0,
                "habilidades": {"python", "docker"}}

        sep = " " * 80
        perfis = [
            ("Ambas avançadas", f"Python avançado, expert.{sep}Docker avançado, produção."),
            ("Ambas sem mod",   f"Python no projeto.{sep}Docker no projeto."),
            ("Ambas básicas",   f"Python básico, aprendendo.{sep}Docker básico, iniciante."),
            ("Python av / Docker bás", f"Python avançado.{sep}Docker básico."),
        ]

        print(f"  {'PERFIL':<26} {'PROFIC DETECTADA':<28} {'BONUS SKILLS'}")
        print(f"{'─'*W}")

        for nome, texto in perfis:
            feat  = extrair_features_curriculo(texto)
            p     = feat["proficiencia_skills"]
            bonus = calcular_bonus_estrutural(feat, vaga)

            py_peso  = p.get("python", "—")
            dk_peso  = p.get("docker", "—")
            profic_str = f"python={py_peso}  docker={dk_peso}"

            # componente skills isolado (sem exp/nível)
            hab_cand  = feat["habilidades"] & vaga["habilidades"]
            if hab_cand:
                peso_total = sum(p.get(s, 1.0) for s in hab_cand)
                ov = peso_total / len(vaga["habilidades"])
                b_skl = ov * 0.08
            else:
                b_skl = -0.15

            print(f"  {nome:<26} {profic_str:<28} {b_skl:+.3f}")

        # ── Sangramento de janela (limitação) ───────────────────────────────
        print(f"\n{'═'*W}")
        print(f"  LIMITAÇÃO: SANGRAMENTO DE JANELA (±70 chars)")
        print(f"  Skills muito próximas fazem o modificador de uma afetar a outra")
        print(f"{'─'*W}")

        casos_sangramento = [
            ("Python avançado, Docker básico",          "skills a ~18 chars — sangra"),
            ("Python avançado.  " + " "*60 + "Docker básico", "skills a 78 chars — sem sangramento"),
        ]

        for texto, descricao in casos_sangramento:
            feat  = extrair_features_curriculo(texto)
            p     = feat["proficiencia_skills"]
            py_p  = p.get("python", "—")
            dk_p  = p.get("docker", "—")
            print(f"  {descricao}")
            print(f"    → python={py_p}  docker={dk_p}  "
                  f"{'⚠ python contaminou!' if py_p == 0.3 else '✓ correto'}")

        print(f"\n{'═'*W}")
        assert True


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

    def test_bonus_maximo_025(self):
        feat_cv   = {"anos_experiencia": 30.0, "nivel_senioridade": 6,
                     "habilidades": {"python", "fastapi", "postgresql", "docker",
                                     "kubernetes", "redis", "aws"}}
        feat_vaga = {"anos_minimos": 1.0, "nivel_esperado": 1,
                     "habilidades": {"python", "fastapi"}}
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) <= 0.25

    def test_penalidade_minima_menos_025(self):
        feat_cv   = {"anos_experiencia": 0.0, "nivel_senioridade": 0, "habilidades": set()}
        feat_vaga = {"anos_minimos": 15.0, "nivel_esperado": 6,
                     "habilidades": {"python", "aws", "kubernetes", "kafka"}}
        assert calcular_bonus_estrutural(feat_cv, feat_vaga) >= -0.25

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
        assert feat["nivel_educacao"] == 3  # graduação concluída

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
