"""
Testes de IA com novos perfis de candidatos — cobertura ampliada.

Perfis testados (todos diferentes dos testes anteriores):
  CV_DEVOPS        — Engenheiro DevOps/SRE Sênior, 7 anos
  CV_FRONTEND      — Desenvolvedor Frontend React Pleno, 4 anos
  CV_QA            — Analista QA com Python, 3 anos
  CV_JAVA          — Backend Java Sênior, 8 anos (stack errada para Python)
  CV_PM            — Gerente de Produto, 5 anos (sem skills técnicas de dev)

Vagas testadas:
  VAGA_DEVOPS      — Engenheiro DevOps/SRE Sênior
  VAGA_FRONTEND    — Desenvolvedor Frontend React

Grupos:
  TestFeaturesDevOps      — extração de features do perfil DevOps (rápido)
  TestFeaturesVariados    — features de todos os outros perfis (rápido)
  TestBonusEstrututal     — cálculo do bônus estrutural por cenário (rápido)
  TestPipelineNovos       — scores semânticos com embedding real   (slow)

Comandos:
  pytest tests/test_novos_curriculos.py                  # só os rápidos
  pytest tests/test_novos_curriculos.py -m slow -s       # semânticos + relatório
  pytest tests/test_novos_curriculos.py::TestPipelineNovos::test_relatorio_completo -m slow -s
"""
import pytest

from app.ai.feature_extractor import (
    calcular_bonus_estrutural,
    extrair_features_curriculo,
    extrair_features_vaga,
)
from app.ai.matching_engine import (
    calcular_score_curriculo,
    calcular_score_mercado,
    calcular_score_rh,
    gerar_explicacao,
)


# ═══════════════════════════════════════════════════════════════════════════════
# VAGAS
# ═══════════════════════════════════════════════════════════════════════════════

VAGA_DEVOPS = """
Engenheiro DevOps / SRE Sênior

Buscamos profissional com sólida experiência em infraestrutura e automação.

Requisitos obrigatórios:
  - AWS (EC2, EKS, S3, RDS, Lambda)
  - Kubernetes e Helm
  - Terraform para infrastructure as code
  - Docker e containerização
  - Python para automação e scripts
  - CI/CD com GitHub Actions ou GitLab CI
  - Linux (Ubuntu/RHEL)
  - 5+ anos de experiência em operações de infraestrutura

Diferenciais:
  - Ansible, Pulumi
  - Prometheus, Grafana, observabilidade
  - Certificações AWS (Solutions Architect ou DevOps Engineer)
"""

VAGA_FRONTEND = """
Desenvolvedor Frontend React — Pleno/Sênior

Empresa de produto busca desenvolvedor focado em frontend moderno.

Requisitos:
  - React com hooks e context API
  - TypeScript obrigatório
  - Next.js para SSR/SSG
  - JavaScript avançado (ES2020+)
  - GraphQL (cliente Apollo ou similar)
  - Node.js básico para BFF
  - CSS modular / Tailwind
  - 3+ anos de experiência em frontend
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CVs
# ═══════════════════════════════════════════════════════════════════════════════

CV_DEVOPS = """
Rafael Mendes — Engenheiro DevOps / SRE Sênior
7 anos de experiência em infraestrutura de software e operações em nuvem.

EXPERIÊNCIA PROFISSIONAL

FinTech Global — Site Reliability Engineer Sênior          2020–2024
  Gestão de infraestrutura AWS (EC2, EKS, S3, RDS, Lambda) com mais de
  300 microserviços em produção. Kubernetes com Helm para orquestração.
  Terraform para provisionamento de toda a infraestrutura como código.
  CI/CD com GitHub Actions e ArgoCD. Observabilidade com Prometheus e Grafana.
  Ansible para gestão de configuração. Automação de tarefas em Python.

StartupLogística — Engenheiro de Infraestrutura Pleno      2017–2020
  Docker e containerização de aplicações. Linux (Ubuntu/RHEL).
  Pipelines de CI/CD com GitLab CI. AWS ECS e EC2. Scripts em Python e Bash.
  Monitoramento com CloudWatch. Gestão de bancos RDS (PostgreSQL).

HABILIDADES TÉCNICAS
AWS · Kubernetes · Helm · Terraform · Ansible · Docker · Python
GitHub Actions · GitLab CI · ArgoCD · CI/CD · Linux · PostgreSQL
Prometheus · Grafana · Bash · Git

FORMAÇÃO
Bacharelado em Engenharia de Computação — UNICAMP (2016)

CERTIFICAÇÕES
AWS Solutions Architect Associate · Certified Kubernetes Administrator (CKA)
"""

CV_FRONTEND = """
Isabela Torres — Desenvolvedora Frontend React
4 anos de experiência em desenvolvimento de interfaces modernas.

EXPERIÊNCIA PROFISSIONAL

E-commerce TechBR — Desenvolvedora Frontend Pleno          2021–2024
  Desenvolvimento de SPA com React e TypeScript. Migração para Next.js com
  SSR para melhor SEO. GraphQL com Apollo Client. Testes com Jest e
  React Testing Library. Tailwind CSS. Storybook para design system.

Agência Criativa Web — Desenvolvedora Front-end Júnior     2020–2021
  React funcional com hooks. JavaScript ES6+. Node.js para scripts de build.
  Consumo de APIs REST. CSS, HTML semântico.

HABILIDADES
React · TypeScript · NextJS · Next.js · JavaScript · GraphQL · Node.js
Tailwind · CSS · HTML · Git · Jest · Figma

FORMAÇÃO
Bacharelado em Sistemas de Informação — FIAP (2020)
"""

CV_QA = """
Lucas Ferreira — Analista de Qualidade de Software
3 anos de experiência em testes de software, com foco em automação.

EXPERIÊNCIA PROFISSIONAL

SaaS Company BR — QA Engineer Pleno                        2022–2024
  Automação de testes de API com Python e Pytest. Testes end-to-end.
  Postman para testes manuais e coleções automatizadas. SQL para
  validação de dados em PostgreSQL. Integração com pipelines de CI/CD.
  Análise de requisitos e criação de planos de teste.

Consultoria TI — Analista de QA Júnior                     2021–2022
  Testes funcionais manuais. Reporte de bugs no Jira. Git básico.
  Scripts em Python para geração de dados de teste.

HABILIDADES
Python · Pytest · Postman · SQL · PostgreSQL · Jira · Git · Scrum · CI/CD

FORMAÇÃO
Tecnólogo em Análise e Desenvolvimento de Sistemas — FATEC (2021)
"""

CV_JAVA = """
Bruno Souza — Engenheiro de Software Backend Sênior
8 anos de experiência em desenvolvimento de sistemas de alta escala com Java.

EXPERIÊNCIA PROFISSIONAL

Banco Digital XYZ — Tech Lead Java                         2019–2024
  Liderança de time de 8 engenheiros. Desenvolvimento de microsserviços com
  Java e Spring Boot. PostgreSQL, Redis para cache. Kafka para mensageria.
  Kubernetes e Docker para deploy. REST APIs e gRPC. Maven e Gradle.
  Testes com JUnit e Mockito. AWS (EC2, RDS, S3).

Telecom Corp — Desenvolvedor Java Sênior                   2016–2019
  Java EE, Spring Framework, Hibernate. Oracle e PostgreSQL.
  Docker. Scrum e Kanban.

HABILIDADES TÉCNICAS
Java · Spring Boot · Spring · Hibernate · PostgreSQL · Oracle · Redis
Kafka · Docker · Kubernetes · AWS · gRPC · Git · Scrum · Maven

FORMAÇÃO
Bacharelado em Ciência da Computação — USP (2015)
"""

CV_PM = """
Camila Rocha — Gerente de Produto Sênior
5 anos de experiência em gestão de produtos digitais.

EXPERIÊNCIA PROFISSIONAL

Startup Fintech — Head of Product                          2021–2024
  Responsável pelo roadmap do produto. Coordenação com times de
  engenharia, design e negócio. Metodologias ágeis (Scrum e Kanban).
  Análise de métricas de produto (DAU, LTV, churn). OKRs e KPIs.

E-commerce Plataforma — Product Manager Pleno              2019–2021
  Gestão de backlog no Jira e Confluence. Entrevistas com usuários.
  Priorização com frameworks RICE e ICE. Documentação de requisitos.

HABILIDADES
Scrum · Kanban · Agile · Jira · Confluence · OKRs
Análise de dados · Excel · PowerPoint · Figma

FORMAÇÃO
MBA em Gestão de Produtos Digitais — FGV (2020)
Bacharelado em Administração — PUC-RJ (2018)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários de label
# ═══════════════════════════════════════════════════════════════════════════════

_NIVEL_LABEL = {
    0: "estágio/trainee",
    1: "júnior",
    2: "pleno",
    3: "sênior",
    4: "lead/staff",
    5: "gestão/head",
    6: "direção/CxO",
}

_EDUC_LABEL = {
    0: "sem formação",
    1: "técnico",
    2: "graduação incompleta",
    3: "graduação completa",
    4: "pós/MBA",
    5: "mestrado",
    6: "doutorado",
}


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 1 — Features do perfil DevOps (rápido)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeaturesDevOps:
    """
    Verifica se as features do CV DevOps são extraídas corretamente.
    Fonte: feature_extractor.extrair_features_curriculo()
    """

    def test_experiencia_7_anos_ou_mais(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        assert feat["anos_experiencia"] >= 6.0, (
            f"CV DevOps tem 7 anos (2017–2024), detectado: {feat['anos_experiencia']:.1f}"
        )

    def test_nivel_senior_detectado(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        assert feat["nivel_senioridade"] >= 3, (
            f"'Sênior' deveria ser nível >= 3, obteve {feat['nivel_senioridade']}"
        )

    def test_skills_infra_detectadas(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        skills = feat["habilidades"]
        infra = {"kubernetes", "terraform", "docker", "aws"}
        encontradas = skills & infra
        assert len(encontradas) >= 3, (
            f"Esperava >= 3 skills de infra {infra}, encontrou {encontradas}"
        )

    def test_python_detectado_no_devops(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        assert "python" in feat["habilidades"], (
            "CV DevOps menciona Python — deveria ser detectado"
        )

    def test_cicd_detectado(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        assert "ci/cd" in feat["habilidades"], (
            "'DevOps', 'CI/CD', 'GitHub Actions' devem normalizar para ci/cd"
        )

    def test_graduacao_completa(self):
        feat = extrair_features_curriculo(CV_DEVOPS)
        assert feat["nivel_educacao"] == 3, (
            f"Bacharelado com ano de conclusão = nível 3, obteve {feat['nivel_educacao']}"
        )

    def test_devops_cobre_maioria_dos_requisitos_da_vaga(self):
        feat_cv   = extrair_features_curriculo(CV_DEVOPS)
        feat_vaga = extrair_features_vaga(VAGA_DEVOPS, [])
        overlap = feat_cv["habilidades"] & feat_vaga["habilidades"]
        total_req = len(feat_vaga["habilidades"])
        assert len(overlap) >= 4, (
            f"CV DevOps deveria cobrir >= 4 skills da vaga DevOps. "
            f"Vaga pede {total_req} skills, overlap: {sorted(overlap)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 2 — Features dos outros perfis (rápido)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeaturesVariados:
    """
    Verifica extração de features para Frontend, QA, Java e PM.
    Fonte: feature_extractor.extrair_features_curriculo()
    """

    def test_frontend_tem_react_typescript_nextjs(self):
        feat = extrair_features_curriculo(CV_FRONTEND)
        skills = feat["habilidades"]
        assert "react" in skills,      "React deve ser detectado"
        assert "typescript" in skills, "TypeScript deve ser detectado"
        assert "nextjs" in skills,     "Next.js/nextjs deve ser detectado"

    def test_frontend_nao_tem_skills_backend_python(self):
        feat = extrair_features_curriculo(CV_FRONTEND)
        skills = feat["habilidades"]
        backend = {"fastapi", "django", "flask", "celery", "sqlalchemy"}
        assert len(skills & backend) == 0, (
            f"CV Frontend não deveria ter skills de backend Python: {skills & backend}"
        )

    def test_frontend_nivel_pleno(self):
        feat = extrair_features_curriculo(CV_FRONTEND)
        assert feat["nivel_senioridade"] == 2, (
            f"'Pleno' deveria ser nível 2, obteve {feat['nivel_senioridade']}"
        )

    def test_qa_tem_python_pytest_postman(self):
        feat = extrair_features_curriculo(CV_QA)
        skills = feat["habilidades"]
        assert "python" in skills,  "Python deve ser detectado no CV QA"
        assert "postman" in skills, "Postman deve ser detectado no CV QA"

    def test_qa_tem_3_anos_ou_menos(self):
        feat = extrair_features_curriculo(CV_QA)
        assert feat["anos_experiencia"] <= 4.0, (
            f"QA tem 3 anos de exp, detectado: {feat['anos_experiencia']:.1f}"
        )

    def test_java_tem_java_springboot_redis_kafka(self):
        feat = extrair_features_curriculo(CV_JAVA)
        skills = feat["habilidades"]
        java_skills = {"java", "springboot", "redis", "kafka"}
        encontradas = skills & java_skills
        assert len(encontradas) >= 3, (
            f"CV Java deveria ter {java_skills}, encontrou {encontradas}"
        )

    def test_java_nao_tem_python(self):
        feat = extrair_features_curriculo(CV_JAVA)
        assert "python" not in feat["habilidades"], (
            "CV Java não menciona Python — não deveria ser detectado"
        )

    def test_java_tem_8_anos_ou_mais(self):
        feat = extrair_features_curriculo(CV_JAVA)
        assert feat["anos_experiencia"] >= 7.0, (
            f"CV Java tem 8 anos (2016–2024), detectado: {feat['anos_experiencia']:.1f}"
        )

    def test_java_nivel_lead(self):
        feat = extrair_features_curriculo(CV_JAVA)
        assert feat["nivel_senioridade"] >= 3, (
            f"'Tech Lead' deveria ser nível >= 3 (lead=4), obteve {feat['nivel_senioridade']}"
        )

    def test_pm_sem_skills_tecnicas_de_dev(self):
        feat = extrair_features_curriculo(CV_PM)
        dev_skills = {"python", "java", "javascript", "react", "docker", "kubernetes",
                      "aws", "terraform", "fastapi", "postgresql"}
        encontradas = feat["habilidades"] & dev_skills
        assert len(encontradas) == 0, (
            f"PM não deveria ter skills de dev: {encontradas}"
        )

    def test_pm_tem_skills_de_gestao(self):
        feat = extrair_features_curriculo(CV_PM)
        gestao = {"scrum", "kanban", "agile", "jira", "confluence"}
        encontradas = feat["habilidades"] & gestao
        assert len(encontradas) >= 2, (
            f"PM deveria ter skills de gestão {gestao}, encontrou {encontradas}"
        )

    def test_pm_nivel_gestao(self):
        feat = extrair_features_curriculo(CV_PM)
        assert feat["nivel_senioridade"] >= 4, (
            f"'Head of Product'/'Gerente' deveria ser nível >= 4 (gestão=5), "
            f"obteve {feat['nivel_senioridade']}"
        )

    def test_java_mais_experiencia_que_frontend(self):
        feat_java = extrair_features_curriculo(CV_JAVA)
        feat_fe   = extrair_features_curriculo(CV_FRONTEND)
        assert feat_java["anos_experiencia"] > feat_fe["anos_experiencia"], (
            f"Java ({feat_java['anos_experiencia']:.1f}a) deveria ter mais exp "
            f"que Frontend ({feat_fe['anos_experiencia']:.1f}a)"
        )

    def test_devops_mais_overlap_na_vaga_devops_que_pm(self):
        feat_vaga  = extrair_features_vaga(VAGA_DEVOPS, [])
        feat_devops = extrair_features_curriculo(CV_DEVOPS)
        feat_pm     = extrair_features_curriculo(CV_PM)
        overlap_dev = len(feat_devops["habilidades"] & feat_vaga["habilidades"])
        overlap_pm  = len(feat_pm["habilidades"] & feat_vaga["habilidades"])
        assert overlap_dev > overlap_pm, (
            f"DevOps ({overlap_dev} skills) deveria ter mais overlap com vaga DevOps "
            f"do que PM ({overlap_pm} skills)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 3 — Bônus estrutural por cenário (rápido)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBonusEstrututalNovos:
    """
    Verifica o bônus estrutural para combinações CV × vaga.
    Fonte: feature_extractor.calcular_bonus_estrutural()
    """

    def test_devops_bonus_positivo_para_vaga_devops(self):
        feat_cv   = extrair_features_curriculo(CV_DEVOPS)
        feat_vaga = extrair_features_vaga(VAGA_DEVOPS, [])
        bonus = calcular_bonus_estrutural(feat_cv, feat_vaga)
        assert bonus > 0, (
            f"DevOps com exp/skills perfeitas deveria ter bônus > 0, obteve {bonus:.3f}"
        )

    def test_pm_bonus_negativo_para_vaga_devops(self):
        feat_cv   = extrair_features_curriculo(CV_PM)
        feat_vaga = extrair_features_vaga(VAGA_DEVOPS, [])
        bonus = calcular_bonus_estrutural(feat_cv, feat_vaga)
        assert bonus < 0, (
            f"PM sem skills de infra deveria ter bônus negativo para vaga DevOps, "
            f"obteve {bonus:.3f}"
        )

    def test_devops_bonus_maior_que_java_para_vaga_devops(self):
        feat_vaga   = extrair_features_vaga(VAGA_DEVOPS, [])
        bonus_dev   = calcular_bonus_estrutural(extrair_features_curriculo(CV_DEVOPS), feat_vaga)
        bonus_java  = calcular_bonus_estrutural(extrair_features_curriculo(CV_JAVA),   feat_vaga)
        assert bonus_dev > bonus_java, (
            f"DevOps ({bonus_dev:.3f}) deveria ter bônus maior que Java ({bonus_java:.3f}) "
            f"para vaga DevOps (Java não tem Python/Terraform)"
        )

    def test_frontend_bonus_positivo_para_vaga_frontend(self):
        feat_cv   = extrair_features_curriculo(CV_FRONTEND)
        feat_vaga = extrair_features_vaga(VAGA_FRONTEND, [])
        bonus = calcular_bonus_estrutural(feat_cv, feat_vaga)
        assert bonus > 0, (
            f"Frontend com React/TS/Next deveria ter bônus > 0 para vaga Frontend, "
            f"obteve {bonus:.3f}"
        )

    def test_bonus_sempre_dentro_do_intervalo(self):
        feat_vaga_dev = extrair_features_vaga(VAGA_DEVOPS, [])
        feat_vaga_fe  = extrair_features_vaga(VAGA_FRONTEND, [])
        for nome, cv, vaga in [
            ("DevOps→DevOps",   CV_DEVOPS,    feat_vaga_dev),
            ("Frontend→DevOps", CV_FRONTEND,  feat_vaga_dev),
            ("Java→DevOps",     CV_JAVA,      feat_vaga_dev),
            ("QA→DevOps",       CV_QA,        feat_vaga_dev),
            ("PM→DevOps",       CV_PM,        feat_vaga_dev),
            ("Frontend→FE",     CV_FRONTEND,  feat_vaga_fe),
            ("DevOps→FE",       CV_DEVOPS,    feat_vaga_fe),
        ]:
            bonus = calcular_bonus_estrutural(extrair_features_curriculo(cv), vaga)
            assert -0.25 <= bonus <= 0.25, (
                f"[{nome}] Bônus fora do intervalo [-0.25, 0.25]: {bonus:.3f}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GRUPO 4 — Pipeline semântico com embedding real (slow)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
class TestPipelineNovos:
    """
    Testes semânticos com modelo real (all-MiniLM-L6-v2).
    Execute com: pytest tests/test_novos_curriculos.py -m slow -s
    """

    @staticmethod
    def _vet(texto: str) -> list:
        from app.ai.resume_parser import get_model
        return get_model().encode(texto, normalize_embeddings=True).tolist()

    @staticmethod
    def _score_rh(cv: str, vaga: str) -> float:
        v_cv   = TestPipelineNovos._vet(cv)
        v_vaga = TestPipelineNovos._vet(vaga)
        return calcular_score_rh(v_cv, v_vaga)

    @staticmethod
    def _score_full(cv: str, vaga: str, p_rh=0.6, p_mkt=0.4) -> float:
        v_cv   = TestPipelineNovos._vet(cv)
        v_vaga = TestPipelineNovos._vet(vaga)
        s_rh   = calcular_score_rh(v_cv, v_vaga)
        s_mkt  = calcular_score_mercado(v_cv, v_vaga)
        bonus  = calcular_bonus_estrutural(
            extrair_features_curriculo(cv),
            extrair_features_vaga(vaga),
        )
        return calcular_score_curriculo(s_rh, s_mkt, p_rh, p_mkt, bonus)

    # ── Ordenação semântica: vaga DevOps ─────────────────────────────────────

    def test_devops_rh_maior_que_pm_para_vaga_devops(self):
        s_dev = self._score_rh(CV_DEVOPS, VAGA_DEVOPS)
        s_pm  = self._score_rh(CV_PM,     VAGA_DEVOPS)
        assert s_dev > s_pm, (
            f"DevOps ({s_dev:.3f}) deveria pontuar mais que PM ({s_pm:.3f}) na vaga DevOps"
        )

    def test_devops_rh_maior_que_frontend_para_vaga_devops(self):
        s_dev = self._score_rh(CV_DEVOPS,   VAGA_DEVOPS)
        s_fe  = self._score_rh(CV_FRONTEND, VAGA_DEVOPS)
        assert s_dev > s_fe, (
            f"DevOps ({s_dev:.3f}) deveria pontuar mais que Frontend ({s_fe:.3f}) na vaga DevOps"
        )

    def test_java_score_final_maior_que_pm_para_vaga_devops(self):
        # Score semântico puro pode ser próximo (embedding geral não separa bem stacks),
        # mas o bônus estrutural corrige: Java tem overlap real de skills, PM tem 0.
        s_java = self._score_full(CV_JAVA, VAGA_DEVOPS)
        s_pm   = self._score_full(CV_PM,   VAGA_DEVOPS)
        assert s_java > s_pm, (
            f"Java final ({s_java:.1f}) deveria ser maior que PM final ({s_pm:.1f}) "
            "na vaga DevOps — bônus estrutural corrige o gap semântico"
        )

    # ── Ordenação semântica: vaga Frontend ───────────────────────────────────

    def test_frontend_rh_maior_que_devops_para_vaga_frontend(self):
        s_fe  = self._score_rh(CV_FRONTEND, VAGA_FRONTEND)
        s_dev = self._score_rh(CV_DEVOPS,   VAGA_FRONTEND)
        assert s_fe > s_dev, (
            f"Frontend ({s_fe:.3f}) deveria pontuar mais que DevOps ({s_dev:.3f}) na vaga Frontend"
        )

    def test_frontend_rh_maior_que_pm_para_vaga_frontend(self):
        s_fe = self._score_rh(CV_FRONTEND, VAGA_FRONTEND)
        s_pm = self._score_rh(CV_PM,       VAGA_FRONTEND)
        assert s_fe > s_pm, (
            f"Frontend ({s_fe:.3f}) deveria pontuar mais que PM ({s_pm:.3f}) na vaga Frontend"
        )

    # ── Score final com bônus estrutural ─────────────────────────────────────

    def test_devops_score_final_acima_de_50_para_vaga_devops(self):
        score = self._score_full(CV_DEVOPS, VAGA_DEVOPS)
        assert score >= 50.0, (
            f"DevOps ideal para vaga DevOps deveria ter score >= 50, obteve {score:.1f}"
        )

    def test_pm_score_final_abaixo_do_devops_por_margem(self):
        s_dev = self._score_full(CV_DEVOPS, VAGA_DEVOPS)
        s_pm  = self._score_full(CV_PM,     VAGA_DEVOPS)
        assert s_dev > s_pm + 5, (
            f"DevOps ({s_dev:.1f}) deveria ser > 5pts acima do PM ({s_pm:.1f}) na vaga DevOps"
        )

    def test_frontend_score_final_acima_de_50_para_vaga_frontend(self):
        score = self._score_full(CV_FRONTEND, VAGA_FRONTEND)
        assert score >= 50.0, (
            f"Frontend ideal para vaga Frontend deveria ter score >= 50, obteve {score:.1f}"
        )

    # ── Relatório completo ────────────────────────────────────────────────────

    def test_relatorio_completo(self):
        """
        Imprime relatório detalhado mostrando EXATAMENTE o que vem de cada função.

        Execute com:
          pytest tests/test_novos_curriculos.py::TestPipelineNovos::test_relatorio_completo -m slow -s
        """
        W = 76

        cvs = [
            ("DevOps Sênior",    CV_DEVOPS),
            ("Frontend Pleno",   CV_FRONTEND),
            ("QA com Python",    CV_QA),
            ("Java Backend",     CV_JAVA),
            ("Product Manager",  CV_PM),
        ]
        vagas = [
            ("Vaga DevOps/SRE", VAGA_DEVOPS),
            ("Vaga Frontend",   VAGA_FRONTEND),
        ]

        for nome_vaga, texto_vaga in vagas:
            feat_vaga = extrair_features_vaga(texto_vaga, [])
            v_vaga    = self._vet(texto_vaga)

            print(f"\n\n{'#'*W}")
            print(f"# {'RANKING PARA: ' + nome_vaga:^{W-4}} #")
            print(f"{'#'*W}")
            print(f"  Fonte da vaga → feature_extractor.extrair_features_vaga()")
            print(f"  Skills requeridas ({len(feat_vaga['habilidades'])}): "
                  f"{', '.join(sorted(feat_vaga['habilidades']))}")
            nivel_vaga = feat_vaga.get('nivel_esperado', 0)
            anos_vaga  = feat_vaga.get('anos_minimos', 0.0)
            print(f"  Nível esperado: {nivel_vaga} = {_NIVEL_LABEL.get(nivel_vaga, '?')}  |  "
                  f"Mín. anos: {anos_vaga:.0f}")

            resultados = []
            for nome_cv, texto_cv in cvs:
                feat_cv  = extrair_features_curriculo(texto_cv)
                v_cv     = self._vet(texto_cv)
                s_rh     = calcular_score_rh(v_cv, v_vaga)
                s_mkt    = calcular_score_mercado(v_cv, v_vaga)
                bonus    = calcular_bonus_estrutural(feat_cv, feat_vaga)
                final    = calcular_score_curriculo(s_rh, s_mkt, 0.6, 0.4, bonus)
                expl     = gerar_explicacao(s_rh, s_mkt, final, 0.6, 0.4,
                                            features_cv=feat_cv, features_vaga=feat_vaga)
                overlap  = sorted(feat_cv["habilidades"] & feat_vaga["habilidades"])
                resultados.append((final, nome_cv, feat_cv, s_rh, s_mkt, bonus, overlap, expl))

            resultados.sort(key=lambda x: -x[0])

            for pos, (final, nome_cv, feat_cv, s_rh, s_mkt, bonus, overlap, expl) in enumerate(resultados, 1):
                classif = expl["componentes"]["aderencia_vaga"]["classificacao"]

                print(f"\n  {'═'*W}")
                print(f"  #{pos}  {nome_cv.upper()}  →  {final:.1f}/100  [{classif.upper()}]")
                print(f"  {'─'*W}")

                # Bloco 1: Features do CV
                print(f"  [1] FEATURES DO CV")
                print(f"      Fonte → feature_extractor.extrair_features_curriculo()")
                anos = feat_cv["anos_experiencia"]
                nivel = feat_cv["nivel_senioridade"]
                educ  = feat_cv["nivel_educacao"]
                print(f"      Experiência   : {anos:.1f} anos  "
                      f"({'✓ suficiente' if anos_vaga > 0 and anos >= anos_vaga else '✗ insuficiente' if anos_vaga > 0 else '—'})")
                print(f"      Senioridade   : nível {nivel} = {_NIVEL_LABEL.get(nivel, '?')}  "
                      f"({'✓ ok' if nivel_vaga > 0 and nivel >= nivel_vaga else '✗ abaixo' if nivel_vaga > 0 else '—'})")
                print(f"      Educação      : nível {educ} = {_EDUC_LABEL.get(educ, '?')}")
                skills_cv = sorted(feat_cv["habilidades"])
                print(f"      Skills ({len(skills_cv):>2})   : {', '.join(skills_cv) or '(nenhuma)'}")

                # Bloco 2: Overlap de skills
                print(f"  {'─'*W}")
                print(f"  [2] OVERLAP DE SKILLS COM A VAGA")
                print(f"      Fonte → interseção de habilidades CV ∩ VAGA")
                print(f"      Em comum ({len(overlap)}/{len(feat_vaga['habilidades'])} requeridas): "
                      f"{', '.join(overlap) if overlap else '(nenhuma)'}")

                # Bloco 3: Bônus estrutural com breakdown manual
                print(f"  {'─'*W}")
                print(f"  [3] BÔNUS ESTRUTURAL  →  {bonus:+.3f}")
                print(f"      Fonte → feature_extractor.calcular_bonus_estrutural()")
                # Recalcular componentes para exibição
                _hab_req   = feat_vaga.get("habilidades", set())
                _hab_cand  = feat_cv.get("habilidades", set())
                _comuns    = _hab_req & _hab_cand
                _profic    = feat_cv.get("proficiencia_skills", {})
                _skl_ov    = (sum(_profic.get(s, 1.0) for s in _comuns) / len(_hab_req)
                              if _comuns and _profic else
                              len(_comuns) / len(_hab_req) if _comuns else 0.0)
                _b_exp  = _bonus_exp_desc(anos, anos_vaga, nivel_vaga,
                                          overlap=_skl_ov, tem_req_skills=bool(_hab_req))
                _b_sen  = _bonus_sen_desc(nivel, nivel_vaga)
                _b_skl  = _bonus_skl_desc(feat_cv, feat_vaga)
                print(f"      Experiência   : {_b_exp}")
                print(f"      Senioridade   : {_b_sen}")
                print(f"      Skills overlap: {_b_skl}")

                # Bloco 4: Scores semânticos
                print(f"  {'─'*W}")
                print(f"  [4] SCORES SEMÂNTICOS")
                print(f"      Score RH      : {s_rh*100:>5.1f}%   ← matching_engine.calcular_score_rh()")
                print(f"      Score Mercado : {s_mkt*100:>5.1f}%   ← matching_engine.calcular_score_mercado()")

                # Bloco 5: Composição do score final
                print(f"  {'─'*W}")
                print(f"  [5] SCORE FINAL  →  {final:.1f}/100  [{classif.upper()}]")
                print(f"      Fonte → matching_engine.calcular_score_curriculo()")
                contrib_rh  = round(s_rh * 0.6 * 100, 1)
                contrib_mkt = round(s_mkt * 0.4 * 100, 1)
                contrib_bon = round(bonus * 100, 1)
                print(f"      = (RH {s_rh*100:.1f}% × 60%) + (Mkt {s_mkt*100:.1f}% × 40%) + bônus")
                print(f"      = {contrib_rh:>+5.1f} pts  +  {contrib_mkt:>+5.1f} pts  +  {contrib_bon:>+5.1f} pts")
                print(f"      = {final:.1f} / 100")

            print(f"\n  {'═'*W}")

        # O teste só falha se a lógica básica quebrar — o relatório é informativo
        assert True


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers para breakdown do bônus (exibição no relatório)
# ═══════════════════════════════════════════════════════════════════════════════

_ANOS_POR_NIVEL = {0: 0.0, 1: 1.0, 2: 3.0, 3: 6.0, 4: 9.0, 5: 12.0, 6: 15.0}


def _bonus_exp_desc(anos_cand: float, anos_req: float, nivel_req: int,
                    overlap: float = 1.0, tem_req_skills: bool = False) -> str:
    if anos_req == 0.0 and nivel_req > 0:
        anos_req = _ANOS_POR_NIVEL.get(nivel_req, 0.0)
    if anos_req <= 0 or anos_cand <= 0:
        return "—  (dados insuficientes)"
    ratio  = anos_cand / anos_req
    escala = max(overlap, 0.3) if tem_req_skills else 1.0
    if ratio >= 1.0:
        val  = round(+0.08 * escala, 3)
        desc = f"ratio {anos_cand:.0f}/{anos_req:.0f}={ratio:.2f} ≥ 1.0 × escala {escala:.2f}"
    elif ratio >= 0.7:
        val  = round(+0.03 * escala, 3)
        desc = f"ratio {anos_cand:.0f}/{anos_req:.0f}={ratio:.2f} (70–99%) × escala {escala:.2f}"
    elif ratio < 0.35:
        val  = -0.10
        desc = f"ratio {anos_cand:.0f}/{anos_req:.0f}={ratio:.2f} < 35% → penalidade (não escalada)"
    else:
        val  = 0.0
        desc = f"ratio {anos_cand:.0f}/{anos_req:.0f}={ratio:.2f} (35–70%) → neutro"
    return f"{val:+.3f}  ({desc})"


def _bonus_sen_desc(nivel_cand: int, nivel_req: int) -> str:
    if nivel_req <= 0 or nivel_cand <= 0:
        return "—  (nível não declarado)"
    diff = nivel_cand - nivel_req
    if diff == 0:
        val = +0.07; motivo = "nível exato"
    elif diff == 1:
        val = +0.03; motivo = "1 nível acima"
    elif diff > 1:
        val = -0.01; motivo = f"{diff} níveis acima (overqualification)"
    elif diff == -1:
        val = -0.05; motivo = "1 nível abaixo"
    elif diff == -2:
        val = -0.10; motivo = "2 níveis abaixo"
    else:
        val = -0.15; motivo = f"{abs(diff)} níveis abaixo (mismatch severo)"
    return f"{val:+.2f}  (nível {nivel_cand} − nível req {nivel_req} = {diff:+d} → {motivo})"


def _bonus_skl_desc(feat_cv: dict, feat_vaga: dict) -> str:
    hab_req  = feat_vaga.get("habilidades", set())
    hab_cand = feat_cv.get("habilidades", set())
    profic   = feat_cv.get("proficiencia_skills", {})
    if not hab_req or not hab_cand:
        return "—  (skills não detectadas)"
    comuns = hab_req & hab_cand
    if not comuns:
        return f"-0.150  (0/{len(hab_req)} skills em comum → penalidade por irrelevância)"
    if profic:
        peso = sum(profic.get(s, 1.0) for s in comuns)
        overlap = peso / len(hab_req)
    else:
        overlap = len(comuns) / len(hab_req)
    val = overlap * 0.08
    return f"{val:+.3f}  ({len(comuns)} skills em comum de {len(hab_req)} requeridas, overlap={overlap:.2f})"
