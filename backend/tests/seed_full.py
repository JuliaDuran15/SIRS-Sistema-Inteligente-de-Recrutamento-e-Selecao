"""
Seed completo — popula o banco com dados realistas e inter-relacionados.

Cria:
  7 usuários  (3 RH, 3 gestores, 1 admin)
 12 vagas     (tech, rh, direito, engenharia, financeiro, marketing, nutrição, idiomas)
 37 candidatos com formações e perfis variados
 ~65 candidaturas distribuídas em TODAS as etapas do pipeline
 Currículos processados (scores reais via embedding)
 Entrevistas agendadas e realizadas com notas e histórico de edições

Rode com:
  docker compose exec api python tests/seed_full.py
"""

import sys
import asyncio
sys.path.insert(0, "/app")

from datetime import date, datetime, timedelta
from sqlalchemy.orm import sessionmaker
from app.db.session import engine, Base
import app.db.base  # noqa — registra todos os models

from app.models.usuario    import Usuario, PapelUsuario
from app.models.vaga       import Vaga
from app.models.candidato  import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo  import Curriculo
from app.models.entrevista import Entrevista
from app.ai.resume_parser  import vetorizar_texto
from app.ai.market_analyzer import analisar_mercado
from app.ai.matching_engine import (
    calcular_score_rh, calcular_score_mercado, calcular_score_curriculo,
    calcular_score_final, gerar_explicacao,
)
from app.ai.feature_extractor import extrair_features_curriculo, extrair_features_vaga
from app.core.auth import hash_senha
from app.core.config import settings

# Garante que a extensão pgvector e todas as tabelas existem antes de qualquer operação
from app.db.init_extensions import criar_extensoes
criar_extensoes()
Base.metadata.create_all(engine)

db = sessionmaker(autocommit=False, autoflush=False, bind=engine,
                  expire_on_commit=False)()

# ─────────────────────────────────────────────────────────────────────────────
def limpar():
    db.query(Entrevista).delete()
    db.query(Curriculo).delete()
    db.query(Candidatura).delete()
    db.query(Candidato).delete()
    db.query(Vaga).delete()
    db.query(Usuario).delete()
    db.commit()
    print("Banco limpo.")


# ─────────────────────────────────────────────────────────────────────────────
def criar_usuarios():
    rows = [
        ("Ana Paula Ramos",    "ana@sirs.com",                 "senha123",           PapelUsuario.RH),
        ("Bruno Mendes",       "bruno@sirs.com",               "senha123",           PapelUsuario.RH),
        ("Julia Duran",        "leitorairritada@gmail.com",    "senha123",           PapelUsuario.RH),
        ("Carlos Andrade",     "carlos@sirs.com",              "senha123",           PapelUsuario.GESTOR),
        ("Daniela Torres",     "daniela@sirs.com",             "senha123",           PapelUsuario.GESTOR),
        ("Eduardo Silva",      "eduardo@sirs.com",             "senha123",           PapelUsuario.GESTOR),
        ("Administrador",      settings.ADMIN_EMAIL,           settings.ADMIN_SENHA, PapelUsuario.ADMIN),
    ]
    usuarios = [
        Usuario(nome=n, email=e, senha_hash=hash_senha(s), papel=p)
        for n, e, s, p in rows
    ]
    db.add_all(usuarios)
    db.commit()
    print(f"  {len(usuarios)} usuários criados.")
    return {u.email: u for u in usuarios}


# ─────────────────────────────────────────────────────────────────────────────
# Gestores atribuídos a cada vaga (emails dos gestores)
# carlos → tech backend/infra | daniela → dados/rh/financeiro | eduardo → fullstack/legal/marketing
GESTORES_POR_VAGA = [
    ["carlos@sirs.com", "daniela@sirs.com"],          # 0: Dev Python
    ["carlos@sirs.com", "eduardo@sirs.com"],           # 1: Full Stack
    ["daniela@sirs.com", "eduardo@sirs.com"],          # 2: Eng. Dados
    ["carlos@sirs.com", "eduardo@sirs.com"],           # 3: DevOps
    ["daniela@sirs.com"],                              # 4: Analista RH
    ["eduardo@sirs.com"],                              # 5: Advogado
    ["carlos@sirs.com"],                               # 6: Eng. Civil
    ["daniela@sirs.com", "eduardo@sirs.com"],          # 7: Financeiro
    ["carlos@sirs.com", "daniela@sirs.com"],           # 8: Product Designer
    ["eduardo@sirs.com"],                              # 9: Marketing
    ["daniela@sirs.com"],                              # 10: Nutricionista
    ["daniela@sirs.com", "eduardo@sirs.com"],          # 11: Professora Idiomas
]

SPECS_VAGAS = [
    {
        "nome": "Desenvolvedor Python Sênior",
        "req": (
            "Buscamos desenvolvedor Python sênior com sólida experiência em FastAPI, "
            "SQLAlchemy, PostgreSQL e Docker. Conhecimento em arquitetura de microsserviços, "
            "Redis, Celery e AWS é diferencial. Inglês intermediário e perfil de liderança técnica."
        ),
    },
    {
        "nome": "Desenvolvedor Full Stack (React + Node.js)",
        "req": (
            "Vaga para full stack com React, TypeScript, Node.js e PostgreSQL. "
            "Experiência com REST APIs, GraphQL, testes automatizados (Jest/Vitest) e "
            "CI/CD via GitHub Actions. Noções de UX e boas práticas de acessibilidade."
        ),
    },
    {
        "nome": "Engenheiro de Dados",
        "req": (
            "Engenheiro de dados com expertise em pipelines ETL, Apache Spark, Airflow, "
            "dbt e AWS (S3, Glue, Redshift). Python avançado, SQL e experiência com "
            "modelagem dimensional. Conhecimento em streaming com Kafka é plus."
        ),
    },
    {
        "nome": "DevOps / SRE Engineer",
        "req": (
            "DevOps/SRE com experiência em Kubernetes, Terraform, Ansible e AWS/GCP. "
            "Domínio de CI/CD (GitHub Actions, ArgoCD), observabilidade (Prometheus, Grafana) "
            "e scripting em Python e Bash. Cultura de SLOs/SLIs e resposta a incidentes."
        ),
    },
    {
        "nome": "Analista de RH — People Analytics",
        "req": (
            "Profissional de RH com foco em People Analytics, recrutamento e seleção, "
            "entrevistas por competências, eSocial e LGPD. Excel avançado, Power BI e "
            "experiência com sistemas ATS (Gupy/Greenhouse). Gestão de clima organizacional."
        ),
    },
    {
        "nome": "Advogado Trabalhista Sênior",
        "req": (
            "Advogado sênior especializado em direito trabalhista, com OAB ativa. "
            "Experiência em contencioso judicial e administrativo, negociação coletiva, "
            "CLTQ, FGTS e eSocial. Domínio do PJe e tribunais regionais. Inglês intermediário."
        ),
    },
    {
        "nome": "Engenheiro Civil — Obras Comerciais",
        "req": (
            "Engenheiro civil com CREA ativo para gestão de obras comerciais e industriais. "
            "AutoCAD, Revit, MS Project e orçamento com SINAPI. Experiência em NR-18, "
            "gestão de equipes de campo e laudos técnicos. Perfil de liderança e organização."
        ),
    },
    {
        "nome": "Analista Financeiro — Controladoria",
        "req": (
            "Analista financeiro com experiência em controladoria, planejamento orçamentário, "
            "IFRS, CPC, SAP FI e Power BI. Excel avançado, fluxo de caixa, DRE e "
            "conciliação bancária. CRC ou em andamento. Atenção a detalhes e visão analítica."
        ),
    },
    {
        "nome": "Product Designer (UX/UI)",
        "req": (
            "Designer com sólida experiência em UX/UI, Figma, prototipação, pesquisa com "
            "usuários e design systems. Conhecimento em acessibilidade (WCAG), testes de "
            "usabilidade e handoff para times de engenharia. Portfólio exigido."
        ),
    },
    {
        "nome": "Analista de Marketing Digital",
        "req": (
            "Analista de marketing digital com experiência em Google Ads, Meta Ads, SEO, "
            "Google Analytics 4, CRM (HubSpot/RD Station) e email marketing. "
            "Criação de conteúdo, copywriting e gestão de social media. Growth hacking é plus."
        ),
    },
    {
        "nome": "Nutricionista Clínica",
        "req": (
            "Nutricionista para atendimento clínico em consultório e ambulatório hospitalar. "
            "CRN ativo obrigatório. Experiência em avaliação nutricional, antropometria e "
            "elaboração de planos alimentares individualizados. Conhecimento em dietoterapia "
            "aplicada a diabetes, hipertensão, obesidade e doenças renais. "
            "Habilidade com software DietPro ou AvaNutri. Educação nutricional em grupo. "
            "Diferencial: nutrição esportiva, nutrição hospitalar e prontuário eletrônico."
        ),
    },
    {
        "nome": "Professora de Idiomas — Inglês e Espanhol",
        "req": (
            "Professora de idiomas para ensino de inglês e espanhol, nível intermediário ao avançado. "
            "Domínio fluente de inglês (C1/C2) e espanhol nativo ou fluente obrigatórios. "
            "Experiência em preparação para exames internacionais: IELTS, TOEFL, DELE e DALF. "
            "Diferenciais: francês, alemão ou mandarim. Certificação CELTA ou equivalente. "
            "Uso de plataformas AVA (Moodle), elaboração de materiais didáticos próprios, "
            "ensino presencial e online. Perfil dinâmico, didático e comprometido."
        ),
    },
]

def criar_vagas(usuarios):
    vagas = []
    for i, s in enumerate(SPECS_VAGAS):
        emails_gestores = GESTORES_POR_VAGA[i]
        ids_gestores = [str(usuarios[e].id) for e in emails_gestores if e in usuarios]
        v = Vaga(
            nome=s["nome"],
            requisitos_texto=s["req"],
            vetor_vaga=vetorizar_texto(s["req"]),
            peso_rh=0.6, peso_mercado=0.4,
            peso_curriculo=0.5, peso_entrevista_rh=0.25, peso_entrevista_tec=0.25,
            status="aberta",
            gestores_ids=ids_gestores,
        )
        vagas.append(v)
    db.add_all(vagas)
    db.commit()

    print(f"  {len(vagas)} vagas criadas. Calculando skills de mercado...")
    for v in vagas:
        try:
            resultado = asyncio.run(analisar_mercado(v.nome))
            v.vetor_mercado   = resultado["vetor_mercado"]
            v.ranking_mercado = {
                "termos"                : resultado["termos_frequentes"],
                "total_vagas_analisadas": resultado["total_vagas_analisadas"],
                "fonte"                 : resultado["fonte"],
            }
            n = len(resultado["termos_frequentes"])
            print(f"    ✓ {v.nome[:45]:<45} {n} termos ({resultado['fonte']})")
        except Exception as e:
            print(f"    ✗ {v.nome[:45]:<45} erro: {e}")
    db.commit()
    return vagas


# ─────────────────────────────────────────────────────────────────────────────
CANDIDATOS_DATA = [
    # Tech — Python
    dict(nome="Lucas Ferreira",     email="lucas.ferreira@email.com",    tel="11991110001",
         nasc=date(1993,4,12), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/lucas-ferreira-dev",
         portfolio="https://github.com/lucasferreira-dev",
         formacao=[{"curso":"Ciência da Computação","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2015}],
         cv="Desenvolvedor Python com 10 anos de experiência. Especialista em FastAPI, SQLAlchemy, PostgreSQL, Docker e AWS. Liderou equipe de 5 devs. Fluente em inglês."),

    dict(nome="Mariana Costa",      email="mariana.costa@email.com",     tel="11991110002",
         nasc=date(1996,7,23), cidade="Campinas",     uf="SP",
         linkedin="https://linkedin.com/in/mariana-costa-backend",
         portfolio="https://github.com/marianacosta",
         formacao=[{"curso":"Sistemas de Informação","instituicao":"UNICAMP","nivel":"graduacao","status":"concluido","ano_conclusao":2018}],
         cv="Backend Python, FastAPI, Django, Redis, Celery, PostgreSQL. 6 anos de experiência. Participou de migração de monolito para microsserviços."),

    dict(nome="Rafael Santos",      email="rafael.santos@email.com",     tel="11991110003",
         nasc=date(1998,1,5),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/rafael-santos-py",
         portfolio=None,
         formacao=[{"curso":"Engenharia de Software","instituicao":"FIAP","nivel":"graduacao","status":"concluido","ano_conclusao":2020}],
         cv="Desenvolvedor Python 3 anos, Django REST, FastAPI, Docker, CI/CD GitHub Actions, PostgreSQL. Inglês intermediário."),

    # Tech — Full Stack
    dict(nome="Camila Rodrigues",   email="camila.rodrigues@email.com",  tel="11991110004",
         nasc=date(1995,9,30), cidade="Rio de Janeiro", uf="RJ",
         linkedin="https://linkedin.com/in/camila-rodrigues-fullstack",
         portfolio="https://camilarodrigues.dev",
         formacao=[{"curso":"Engenharia da Computação","instituicao":"PUC-Rio","nivel":"graduacao","status":"concluido","ano_conclusao":2017}],
         cv="Full stack React, TypeScript, Node.js, GraphQL, PostgreSQL. 8 anos de experiência. Jest, Vitest, GitHub Actions CI/CD. Inglês fluente."),

    dict(nome="Felipe Alves",       email="felipe.alves@email.com",      tel="11991110005",
         nasc=date(1997,3,18), cidade="Belo Horizonte", uf="MG",
         linkedin="https://linkedin.com/in/felipe-alves-frontend",
         portfolio="https://github.com/felipealves-ui",
         formacao=[{"curso":"Análise e Desenvolvimento de Sistemas","instituicao":"FATEC","nivel":"tecnologo","status":"concluido","ano_conclusao":2019}],
         cv="Frontend React, TypeScript, Redux, Styled-components. Backend Node.js, Express, MongoDB. 5 anos. Experiência com acessibilidade e design systems."),

    dict(nome="Isabela Nunes",      email="isabela.nunes@email.com",     tel="11991110006",
         nasc=date(1999,11,8), cidade="Recife",         uf="PE",
         linkedin="https://linkedin.com/in/isabela-nunes",
         portfolio=None,
         formacao=[{"curso":"Ciência da Computação","instituicao":"UFPE","nivel":"graduacao","status":"em_andamento","ano_conclusao":None}],
         cv="Desenvolvedora fullstack júnior, React, Vue.js, Node.js, MySQL. 2 anos. Projetos pessoais e estágio em startup."),

    # Tech — Dados
    dict(nome="André Oliveira",     email="andre.oliveira@email.com",    tel="11991110007",
         nasc=date(1991,6,14), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/andre-oliveira-data",
         portfolio="https://github.com/andreoliveira-eng",
         formacao=[{"curso":"Estatística","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2013},
                   {"curso":"Engenharia de Dados","instituicao":"IGTI","nivel":"especializacao","status":"concluido","ano_conclusao":2018}],
         cv="Engenheiro de dados sênior. Apache Spark, Airflow, dbt, AWS Glue/Redshift/S3, Python, SQL avançado, Kafka. 12 anos de experiência."),

    dict(nome="Tatiane Lima",       email="tatiane.lima@email.com",      tel="11991110008",
         nasc=date(1994,2,27), cidade="Curitiba",      uf="PR",
         linkedin="https://linkedin.com/in/tatiane-lima-dados",
         portfolio=None,
         formacao=[{"curso":"Ciência de Dados","instituicao":"PUCPR","nivel":"graduacao","status":"concluido","ano_conclusao":2016}],
         cv="Data engineer com 7 anos. Python, PySpark, Airflow, Redshift, dbt, Terraform AWS. Experiência com modelagem dimensional e Data Mesh."),

    dict(nome="Gabriel Martins",    email="gabriel.martins@email.com",   tel="11991110009",
         nasc=date(2000,5,3),  cidade="Porto Alegre",  uf="RS",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Engenharia de Computação","instituicao":"PUCRS","nivel":"graduacao","status":"concluido","ano_conclusao":2022}],
         cv="Analista de dados 2 anos. Python, pandas, SQL, Power BI. Projetos de ETL simples e visualização."),

    # Tech — DevOps
    dict(nome="Bruno Carvalho",     email="bruno.carvalho@email.com",    tel="11991110010",
         nasc=date(1990,8,22), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/bruno-carvalho-sre",
         portfolio="https://github.com/brunocarvalho-ops",
         formacao=[{"curso":"Redes de Computadores","instituicao":"SENAI","nivel":"tecnologo","status":"concluido","ano_conclusao":2012}],
         cv="DevOps sênior. Kubernetes, Terraform, Ansible, AWS, GCP, ArgoCD, Prometheus, Grafana, Python, Bash. 13 anos. SRE culture, SLO/SLI."),

    dict(nome="Fernanda Souza",     email="fernanda.souza@email.com",    tel="11991110011",
         nasc=date(1993,12,9), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/fernanda-souza-devops",
         portfolio=None,
         formacao=[{"curso":"Engenharia de Software","instituicao":"Mackenzie","nivel":"graduacao","status":"concluido","ano_conclusao":2015}],
         cv="SRE/DevOps 8 anos. Kubernetes, Docker, Terraform, CI/CD GitHub Actions, AWS EKS, observabilidade com Prometheus e Grafana."),

    dict(nome="Ricardo Pereira",    email="ricardo.pereira@email.com",   tel="11991110012",
         nasc=date(2001,4,17), cidade="Florianópolis", uf="SC",
         linkedin="https://linkedin.com/in/ricardo-pereira-infra",
         portfolio=None,
         formacao=[{"curso":"Ciência da Computação","instituicao":"UFSC","nivel":"graduacao","status":"em_andamento","ano_conclusao":None}],
         cv="Estagiário DevOps 1 ano. Docker, CI/CD básico, Linux, Bash scripting. Aprendendo Kubernetes e Terraform."),

    # RH
    dict(nome="Juliana Mendes",     email="juliana.mendes@email.com",    tel="11991110013",
         nasc=date(1992,10,4), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/juliana-mendes-rh",
         portfolio=None,
         formacao=[{"curso":"Psicologia","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2014},
                   {"curso":"MBA RH","instituicao":"FGV","nivel":"mba","status":"concluido","ano_conclusao":2017}],
         cv="Analista de RH sênior. Recrutamento e seleção, People Analytics, Power BI, Gupy, eSocial, LGPD, entrevistas por competências. 10 anos."),

    dict(nome="Patricia Gomes",     email="patricia.gomes@email.com",    tel="11991110014",
         nasc=date(1995,3,21), cidade="Campinas",      uf="SP",
         linkedin="https://linkedin.com/in/patricia-gomes-rh",
         portfolio=None,
         formacao=[{"curso":"Administração com ênfase em RH","instituicao":"PUC-Campinas","nivel":"graduacao","status":"concluido","ano_conclusao":2017}],
         cv="Analista de RH pleno. Recrutamento, onboarding, clima organizacional, eSocial, Excel avançado, ATS Greenhouse. 6 anos."),

    dict(nome="Thiago Barbosa",     email="thiago.barbosa@email.com",    tel="11991110015",
         nasc=date(1998,8,11), cidade="Rio de Janeiro", uf="RJ",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Recursos Humanos","instituicao":"SENAC-RJ","nivel":"tecnologo","status":"concluido","ano_conclusao":2020}],
         cv="RH júnior. Recrutamento básico, triagem de currículos, agendamento de entrevistas, controle de eSocial. 3 anos."),

    # Direito
    dict(nome="Amanda Ribeiro",     email="amanda.ribeiro@email.com",    tel="11991110016",
         nasc=date(1988,5,15), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/amanda-ribeiro-adv",
         portfolio=None,
         formacao=[{"curso":"Direito","instituicao":"PUC-SP","nivel":"graduacao","status":"concluido","ano_conclusao":2010},
                   {"curso":"Direito Trabalhista","instituicao":"Mackenzie","nivel":"especializacao","status":"concluido","ano_conclusao":2013}],
         cv="Advogada trabalhista sênior. OAB ativa. Contencioso judicial TST e TRTs, negociação coletiva, eSocial, FGTS, PJe. 15 anos. Inglês fluente."),

    dict(nome="Rodrigo Teixeira",   email="rodrigo.teixeira@email.com",  tel="11991110017",
         nasc=date(1991,9,7),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/rodrigo-teixeira-trabalhista",
         portfolio=None,
         formacao=[{"curso":"Direito","instituicao":"Mackenzie","nivel":"graduacao","status":"concluido","ano_conclusao":2013}],
         cv="Advogado trabalhista pleno. OAB ativa. Reclamações trabalhistas, audiências, cálculos trabalhistas, eSocial, CLTQ. 10 anos."),

    dict(nome="Larissa Freitas",    email="larissa.freitas@email.com",   tel="11991110018",
         nasc=date(1997,1,29), cidade="Brasília",      uf="DF",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Direito","instituicao":"UnB","nivel":"graduacao","status":"concluido","ano_conclusao":2019}],
         cv="Advogada júnior. OAB ativa. Revisão de contratos, triagem processual, PJe, CPC básico. 3 anos."),

    # Engenharia Civil
    dict(nome="Gustavo Araújo",     email="gustavo.araujo@email.com",    tel="11991110019",
         nasc=date(1987,7,6),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/gustavo-araujo-eng",
         portfolio=None,
         formacao=[{"curso":"Engenharia Civil","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2010}],
         cv="Engenheiro civil sênior. CREA ativo. Gestão de obras comerciais e industriais, AutoCAD, Revit, BIM, MS Project, SINAPI, NR-18. 16 anos."),

    dict(nome="Beatriz Castro",     email="beatriz.castro@email.com",    tel="11991110020",
         nasc=date(1994,11,18),cidade="Belo Horizonte", uf="MG",
         linkedin="https://linkedin.com/in/beatriz-castro-civil",
         portfolio=None,
         formacao=[{"curso":"Engenharia Civil","instituicao":"UFMG","nivel":"graduacao","status":"concluido","ano_conclusao":2016}],
         cv="Engenheira civil plena. CREA ativo. AutoCAD, Revit, gestão de obras residenciais, orçamento SINAPI, topografia. 7 anos."),

    dict(nome="Diego Monteiro",     email="diego.monteiro@email.com",    tel="11991110021",
         nasc=date(1999,3,25), cidade="Curitiba",      uf="PR",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Engenharia Civil","instituicao":"UTFPR","nivel":"graduacao","status":"concluido","ano_conclusao":2022}],
         cv="Engenheiro civil júnior. AutoCAD, MS Project básico, CREA em processo de registro. Experiência em estágio em construtora. 1 ano."),

    # Financeiro
    dict(nome="Vanessa Correia",    email="vanessa.correia@email.com",   tel="11991110022",
         nasc=date(1990,6,3),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/vanessa-correia-controladoria",
         portfolio=None,
         formacao=[{"curso":"Ciências Contábeis","instituicao":"FEA-USP","nivel":"graduacao","status":"concluido","ano_conclusao":2012},
                   {"curso":"Controladoria e Finanças","instituicao":"FGV","nivel":"mba","status":"concluido","ano_conclusao":2015}],
         cv="Analista financeira sênior. Controladoria, IFRS, CPC, SAP FI, Power BI, DRE, fluxo de caixa, conciliação bancária. CRC ativo. 13 anos."),

    dict(nome="Leonardo Azevedo",   email="leonardo.azevedo@email.com",  tel="11991110023",
         nasc=date(1993,8,14), cidade="Rio de Janeiro", uf="RJ",
         linkedin="https://linkedin.com/in/leonardo-azevedo-financas",
         portfolio=None,
         formacao=[{"curso":"Administração","instituicao":"FGV-RJ","nivel":"graduacao","status":"concluido","ano_conclusao":2015}],
         cv="Analista financeiro pleno. Planejamento orçamentário, Excel avançado, Power BI, SAP FI, conciliação, fluxo de caixa. 8 anos."),

    dict(nome="Renata Moreira",     email="renata.moreira@email.com",    tel="11991110024",
         nasc=date(1997,5,20), cidade="São Paulo",     uf="SP",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Ciências Contábeis","instituicao":"Mackenzie","nivel":"graduacao","status":"concluido","ano_conclusao":2019}],
         cv="Analista financeira júnior. Excel avançado, conciliação bancária, ERP TOTVS, relatórios gerenciais. CRC em andamento. 4 anos."),

    # Design UX/UI
    dict(nome="Stephanie Ramos",    email="stephanie.ramos@email.com",   tel="11991110025",
         nasc=date(1995,2,8),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/stephanie-ramos-ux",
         portfolio="https://behance.net/stephanieramos",
         formacao=[{"curso":"Design Digital","instituicao":"ESPM","nivel":"graduacao","status":"concluido","ano_conclusao":2017}],
         cv="Product designer sênior. Figma, prototipação, pesquisa com usuários, design system, testes de usabilidade, acessibilidade WCAG. 8 anos."),

    dict(nome="Henrique Barros",    email="henrique.barros@email.com",   tel="11991110026",
         nasc=date(1998,9,12), cidade="Rio de Janeiro", uf="RJ",
         linkedin="https://linkedin.com/in/henrique-barros-design",
         portfolio="https://behance.net/henriquebarros",
         formacao=[{"curso":"Design Gráfico","instituicao":"PUC-Rio","nivel":"graduacao","status":"concluido","ano_conclusao":2020}],
         cv="UX/UI designer pleno. Figma, design de interfaces, pesquisa qualitativa, prototipação, handoff para devs. 5 anos."),

    dict(nome="Alice Fernandes",    email="alice.fernandes@email.com",   tel="11991110027",
         nasc=date(2001,7,31), cidade="Campinas",      uf="SP",
         linkedin="https://linkedin.com/in/alice-fernandes-design",
         portfolio="https://alicefernandes.myportfolio.com",
         formacao=[{"curso":"Design","instituicao":"UNICAMP","nivel":"graduacao","status":"em_andamento","ano_conclusao":None}],
         cv="Designer júnior. Figma, Adobe XD, noções de pesquisa com usuários. 1 ano e meio."),

    # Marketing
    dict(nome="Carolina Lima",      email="carolina.lima@email.com",     tel="11991110028",
         nasc=date(1992,4,16), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/carolina-lima-marketing",
         portfolio=None,
         formacao=[{"curso":"Publicidade e Propaganda","instituicao":"ESPM","nivel":"graduacao","status":"concluido","ano_conclusao":2014}],
         cv="Analista de marketing digital sênior. Google Ads, Meta Ads, SEO, GA4, HubSpot, email marketing, copywriting, growth hacking. 11 anos."),

    dict(nome="Marcos Vieira",      email="marcos.vieira@email.com",     tel="11991110029",
         nasc=date(1996,11,22),cidade="Curitiba",      uf="PR",
         linkedin="https://linkedin.com/in/marcos-vieira-mkt",
         portfolio=None,
         formacao=[{"curso":"Marketing","instituicao":"FAE","nivel":"graduacao","status":"concluido","ano_conclusao":2018}],
         cv="Analista de marketing digital pleno. Google Analytics, Google Ads, Meta Ads, RD Station, SEO on-page, gestão de redes sociais. 6 anos."),

    dict(nome="Priscila Sousa",     email="priscila.sousa@email.com",    tel="11991110030",
         nasc=date(1999,6,5),  cidade="Fortaleza",     uf="CE",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Comunicação Social","instituicao":"UFC","nivel":"graduacao","status":"concluido","ano_conclusao":2021}],
         cv="Marketing digital júnior. Social media, criação de conteúdo, Google Analytics básico, Canva. 2 anos."),

    # Nutrição — candidatos para testar detecção de skills nutricionais (30–32)
    dict(nome="Beatriz Nogueira",   email="beatriz.nogueira@email.com",  tel="11991110034",
         nasc=date(1989,5,8),  cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/beatriz-nogueira-nutri",
         portfolio=None,
         formacao=[{"curso":"Nutrição","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2011},
                   {"curso":"Nutrição Clínica e Esportiva","instituicao":"GANEP","nivel":"especializacao","status":"concluido","ano_conclusao":2014}],
         cv=(
             "Nutricionista clínica sênior com 14 anos de experiência. CRN ativo. "
             "Avaliação nutricional e antropometria. Elaboração de planos alimentares individualizados. "
             "Dietoterapia aplicada a diabetes, hipertensão e obesidade. "
             "Nutrição esportiva e nutrição hospitalar. Software DietPro avançado. "
             "Educação nutricional em grupo e prontuário eletrônico. "
             "Docência em cursos de pós-graduação em nutrição clínica."
         )),

    dict(nome="Camila Nascimento",  email="camila.nascimento@email.com", tel="11991110035",
         nasc=date(1994,9,14), cidade="Campinas",      uf="SP",
         linkedin="https://linkedin.com/in/camila-nascimento-nutri",
         portfolio=None,
         formacao=[{"curso":"Nutrição","instituicao":"UNICAMP","nivel":"graduacao","status":"concluido","ano_conclusao":2016}],
         cv=(
             "Nutricionista plena com 7 anos de experiência em nutrição hospitalar e clínica. "
             "CRN ativo. Avaliação nutricional e plano alimentar para pacientes com doenças renais e oncológicas. "
             "Antropometria e triagem nutricional. AvaNutri e prontuário eletrônico. "
             "Experiência em UTI e enfermarias. Educação nutricional e orientação alimentar."
         )),

    dict(nome="Renato Cavalcante",  email="renato.cavalcante@email.com", tel="11991110036",
         nasc=date(2000,2,21), cidade="Recife",         uf="PE",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Nutrição","instituicao":"UFPE","nivel":"graduacao","status":"concluido","ano_conclusao":2022}],
         cv=(
             "Nutricionista júnior com 2 anos de experiência em consultório particular. "
             "CRN ativo. Atendimento clínico, avaliação nutricional básica e planos alimentares. "
             "Foco em educação nutricional e reeducação alimentar. DietBox. "
             "Interesse em nutrição esportiva. Excel e Google Workspace."
         )),

    # Idiomas — candidatos para testar detecção de skills de línguas (33–35)
    dict(nome="Sofia Andrade",      email="sofia.andrade@email.com",     tel="11991110031",
         nasc=date(1990,3,14), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/sofia-andrade-idiomas",
         portfolio=None,
         formacao=[{"curso":"Letras — Inglês","instituicao":"USP","nivel":"graduacao","status":"concluido","ano_conclusao":2012},
                   {"curso":"Língua e Cultura Espanhola","instituicao":"Universidad de Salamanca","nivel":"especializacao","status":"concluido","ano_conclusao":2015}],
         cv=(
             "Professora de inglês e espanhol com 12 anos de experiência em cursos de idiomas e corporativo. "
             "Certificação CELTA (Cambridge) e DELE C2 (espanhol). "
             "Inglês fluente (C2) e espanhol nativo. Noções de francês e italiano. "
             "Preparação para IELTS, TOEFL e DELE. Uso avançado de Moodle e Google Classroom. "
             "Elaboração de materiais didáticos próprios. Ensino presencial e online."
         )),

    dict(nome="Pedro Yamamoto",     email="pedro.yamamoto@email.com",    tel="11991110032",
         nasc=date(1988,7,22), cidade="São Paulo",     uf="SP",
         linkedin=None,
         portfolio=None,
         formacao=[{"curso":"Letras — Português/Inglês","instituicao":"UNIFESP","nivel":"graduacao","status":"concluido","ano_conclusao":2011}],
         cv=(
             "Professor de inglês com 13 anos de experiência. Certificação CELTA. "
             "English fluent (C2), japonês nativo (N1). "
             "Preparação para IELTS e TOEFL. Sem domínio de espanhol ou outras línguas latinas. "
             "Experiência em escola de idiomas e aulas particulares. Moodle e Zoom."
         )),

    dict(nome="Marie Dupont",       email="marie.dupont@email.com",      tel="11991110033",
         nasc=date(1993,11,5), cidade="Rio de Janeiro", uf="RJ",
         linkedin="https://linkedin.com/in/marie-dupont-idiomas",
         portfolio=None,
         formacao=[{"curso":"Letras — Francês/Português","instituicao":"UFRJ","nivel":"graduacao","status":"concluido","ano_conclusao":2015}],
         cv=(
             "Professora de francês e inglês com 8 anos de experiência. "
             "Francês nativo (C2), inglês fluente (C1), espanhol intermediário (B2), alemão básico (A2). "
             "Certificação DALF C2 e Cambridge CPE. Preparação para DELF/DALF e Cambridge Exams. "
             "Experiência em cursos livres, colégio bilíngue e preparatório para vestibular. "
             "Moodle, Teams e materiais autorais."
         )),

    # índice 36 — candidata real
    dict(nome="Julia Duran",        email="juliaduran1515@gmail.com",    tel="11991110038",
         nasc=date(2000,1,15), cidade="São Paulo",     uf="SP",
         linkedin="https://linkedin.com/in/julia-machado-duran-791317253",
         portfolio="https://github.com/JuliaDuran15",
         formacao=[{"curso":"Ciência da Computação","instituicao":"UFRJ","nivel":"graduacao","status":"em_andamento","ano_conclusao":None}],
         cv=(
             "Desenvolvedora Python com 3 anos de experiência em projetos de backend. "
             "FastAPI, SQLAlchemy, PostgreSQL, Docker e Docker Compose. "
             "APIs REST com autenticação JWT, testes automatizados com pytest. "
             "CI/CD com GitHub Actions. Redis e Celery em projetos acadêmicos. "
             "Inglês técnico para leitura de documentação. "
             "Interesse em IA aplicada e NLP."
         )),
]

def criar_candidatos():
    candidatos = []
    for d in CANDIDATOS_DATA:
        c = Candidato(
            nome=d["nome"], email=d["email"], telefone=d["tel"],
            data_nascimento=d["nasc"],
            cidade=d["cidade"], estado=d["uf"],
            formacao=d["formacao"],
            linkedin_url=d.get("linkedin"),
            portfolio_url=d.get("portfolio"),
        )
        candidatos.append(c)
    db.add_all(candidatos)
    db.commit()
    print(f"  {len(candidatos)} candidatos criados.")
    return candidatos


# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento: qual candidato se candidata a qual vaga
# (índice candidato, índice vaga, etapa_pipeline)
# Etapas: "novo","triagem_pendente","reprovado_triagem","aprovado_triagem",
#         "rh_agendada","rh_realizada","tec_agendada","tec_realizada",
#         "decisao_pendente","contratado","nao_aprovado","banco_talentos"

VINCULOS = [
    # ── Dev Python (vaga 0) ───────────────────────────────────────────────────
    (0,  0, "contratado"),          # Lucas (sênior)       → contratado
    (1,  0, "tec_realizada"),       # Mariana              → aguardando decisão
    (2,  0, "rh_realizada"),        # Rafael               → entrev. técnica
    (5,  0, "reprovado_triagem"),   # Isabela (fullstack)  → reprovada
    (12, 0, "banco_talentos"),      # Juliana (RH)         → banco talentos

    # ── Full Stack (vaga 1) ───────────────────────────────────────────────────
    (3,  1, "contratado"),          # Camila               → contratada
    (4,  1, "tec_agendada"),        # Felipe               → técnica agendada
    (5,  1, "aprovado_triagem"),    # Isabela              → aprovada triagem
    (0,  1, "nao_aprovado"),        # Lucas (Py puro)      → não aprovado
    (25, 1, "banco_talentos"),      # Henrique (design)    → banco talentos

    # ── Engenheiro de Dados (vaga 2) ──────────────────────────────────────────
    (6,  2, "contratado"),          # André (sênior)       → contratado
    (7,  2, "decisao_pendente"),    # Tatiane              → decisão pendente
    (8,  2, "rh_realizada"),        # Gabriel              → entrev. técnica
    (0,  2, "tec_agendada"),        # Lucas (Python)       → técnica agendada
    (1,  2, "aprovado_triagem"),    # Mariana              → aprovada

    # ── DevOps (vaga 3) ───────────────────────────────────────────────────────
    (9,  3, "contratado"),          # Bruno                → contratado
    (10, 3, "tec_realizada"),       # Fernanda             → aguardando decisão
    (11, 3, "rh_agendada"),         # Ricardo (júnior)     → RH agendada
    (0,  3, "rh_realizada"),        # Lucas                → RH realizada
    (6,  3, "reprovado_triagem"),   # André (dados)        → reprovado

    # ── Analista RH (vaga 4) ──────────────────────────────────────────────────
    (12, 4, "contratada"),          # Juliana              → contratada
    (13, 4, "decisao_pendente"),    # Patricia             → decisão pendente
    (14, 4, "rh_realizada"),        # Thiago               → aguarda técnica
    (3,  4, "reprovado_triagem"),   # Camila (dev)         → reprovada
    (21, 4, "triagem_pendente"),    # Vanessa (financeiro) → triagem

    # ── Advogado Trabalhista (vaga 5) ─────────────────────────────────────────
    (15, 5, "contratada"),          # Amanda               → contratada
    (16, 5, "tec_realizada"),       # Rodrigo              → aguardando decisão
    (17, 5, "rh_agendada"),         # Larissa              → RH agendada
    (12, 5, "reprovado_triagem"),   # Juliana (RH)         → reprovada
    (0,  5, "banco_talentos"),      # Lucas (dev)          → banco talentos

    # ── Engenheiro Civil (vaga 6) ─────────────────────────────────────────────
    (18, 6, "contratado"),          # Gustavo              → contratado
    (19, 6, "tec_realizada"),       # Beatriz              → aguardando decisão
    (20, 6, "rh_realizada"),        # Diego                → entrev. técnica
    (21, 6, "reprovado_triagem"),   # Vanessa (financeiro) → reprovada
    (9,  6, "banco_talentos"),      # Bruno (devops)       → banco talentos

    # ── Analista Financeiro (vaga 7) ──────────────────────────────────────────
    (21, 7, "contratada"),          # Vanessa              → contratada
    (22, 7, "decisao_pendente"),    # Leonardo             → decisão pendente
    (23, 7, "rh_realizada"),        # Renata               → aguarda técnica
    (15, 7, "reprovado_triagem"),   # Amanda (direito)     → reprovada
    (13, 7, "triagem_pendente"),    # Patricia (RH)        → triagem

    # ── Product Designer (vaga 8) ─────────────────────────────────────────────
    (24, 8, "contratada"),          # Stephanie            → contratada
    (25, 8, "tec_agendada"),        # Henrique             → técnica agendada
    (26, 8, "aprovado_triagem"),    # Alice                → aprovada
    (3,  8, "reprovado_triagem"),   # Camila (dev)         → reprovada
    (27, 8, "novo"),                # Carolina (mktg)      → nova

    # ── Marketing Digital (vaga 9) ────────────────────────────────────────────
    (27, 9, "contratada"),          # Carolina             → contratada
    (28, 9, "rh_realizada"),        # Marcos               → aguarda técnica
    (29, 9, "aprovado_triagem"),    # Priscila             → aprovada
    (24, 9, "banco_talentos"),      # Stephanie (design)   → banco talentos
    (12, 9, "triagem_pendente"),    # Juliana (RH)         → triagem

    # ── Nutricionista Clínica (vaga 10) ───────────────────────────────────────
    (30, 10, "contratada"),         # Beatriz N. (sênior, DietPro)    → contratada
    (31, 10, "tec_realizada"),      # Camila N. (plena, hospitalar)   → aguardando decisão
    (32, 10, "aprovado_triagem"),   # Renato N. (júnior, esp. esp.)   → aprovado triagem
    (13, 10, "reprovado_triagem"),  # Patricia (RH, sem nutrição)     → reprovada
    (22, 10, "triagem_pendente"),   # Leonardo (financeiro)           → triagem

    # ── Professora de Idiomas (vaga 11) ───────────────────────────────────────
    (33, 11, "contratada"),         # Sofia (inglês+esp. C2)       → contratada
    (34, 11, "tec_realizada"),      # Pedro (inglês C2, sem esp.)  → aguardando decisão
    (35, 11, "aprovado_triagem"),   # Marie (fr nativo+ing+esp B2) → aprovada triagem
    (13, 11, "reprovado_triagem"),  # Patricia (RH, sem idiomas)   → reprovada
    (17, 11, "triagem_pendente"),   # Larissa (direito)            → triagem

    # ── Dev Python (vaga 0) — Julia Duran candidata ───────────────────────────
    (36,  0, "triagem_pendente"),   # Julia Duran (Python pleno)   → aguardando triagem
]

# ─────────────────────────────────────────────────────────────────────────────
def _score(cv_texto: str, vaga: Vaga) -> tuple[float, float, float, dict]:
    vetor_cv  = vetorizar_texto(cv_texto)
    s_rh      = calcular_score_rh(vetor_cv, vaga.vetor_vaga)
    vm        = vaga.vetor_mercado if vaga.vetor_mercado is not None else vaga.vetor_vaga
    s_mkt     = calcular_score_mercado(vetor_cv, vm)
    s_curric  = calcular_score_curriculo(s_rh, s_mkt, vaga.peso_rh, vaga.peso_mercado)
    termos    = [t for t, _ in (vaga.ranking_mercado or {}).get("termos", [])]
    expl      = gerar_explicacao(
        s_rh, s_mkt, s_curric, vaga.peso_rh, vaga.peso_mercado,
        features_cv   = extrair_features_curriculo(cv_texto),
        features_vaga = extrair_features_vaga(vaga.requisitos_texto, termos),
    )
    return round(s_rh * 100, 1), round(s_mkt * 100, 1), s_curric, expl


def _ago(dias: int, horas: int = 0) -> datetime:
    return datetime.utcnow() - timedelta(days=dias, hours=horas)


def _daqui(dias: int, horas: int = 0) -> datetime:
    return datetime.utcnow() + timedelta(days=dias, hours=horas)


NOTAS_RH = [
    ("Candidato comunicativo, demonstrou bom fit cultural e histórico sólido.",
     ["comunicação", "cultura fit", "pontualidade"], ["poucos detalhes técnicos"]),
    ("Boa apresentação pessoal, experiências bem descritas. Expectativa salarial dentro da faixa.",
     ["apresentação", "clareza", "alinhamento salarial"], ["timidez inicial"]),
    ("Excelente bagagem. Demonstrou liderança e iniciativa em projetos anteriores.",
     ["liderança", "iniciativa", "senioridade"], []),
    ("Perfil alinhado com a vaga, motivação alta, histórico de estabilidade.",
     ["motivação", "estabilidade", "aderência ao cargo"], ["experiência em empresa menor"]),
    ("Comunicação clara, respostas objetivas sobre desafios técnicos.",
     ["objetividade", "autoconhecimento"], ["sem experiência internacional"]),
]

NOTAS_TEC = [
    ("Resolveu os desafios técnicos propostos com eficiência. Domina as tecnologias da vaga.",
     ["raciocínio técnico", "profundidade", "resolução de problemas"], ["documentação fraca"]),
    ("Demonstrou conhecimento sólido e fez boas perguntas sobre arquitetura do sistema.",
     ["arquitetura", "curiosidade técnica", "proatividade"], ["pouca experiência com cloud"]),
    ("Impressionou na parte prática. Código limpo e bem organizado.",
     ["código limpo", "boas práticas", "atenção a detalhes"], []),
    ("Boa base teórica mas precisaria de ramp-up nas ferramentas específicas.",
     ["base sólida", "aprendizado rápido"], ["lacuna nas ferramentas", "pouca experiência com o stack"]),
    ("Excelente desenvolvedor, acima da média. Trouxe ideias novas durante a entrevista.",
     ["inovação", "senioridade técnica", "visão de produto"], []),
]


def criar_candidaturas(vagas, candidatos, usuarios):
    ana     = usuarios["ana@sirs.com"]
    bruno   = usuarios["bruno@sirs.com"]
    julia   = usuarios["leitorairritada@gmail.com"]
    carlos  = usuarios["carlos@sirs.com"]
    daniela = usuarios["daniela@sirs.com"]
    eduardo = usuarios["eduardo@sirs.com"]

    rhs     = [ana, bruno, julia]
    gestores= [carlos, daniela, eduardo]

    criadas = []

    for idx_c, idx_v, etapa in VINCULOS:
        cand = candidatos[idx_c]
        vaga = vagas[idx_v]
        cv   = CANDIDATOS_DATA[idx_c]["cv"]
        rh   = rhs[idx_c % 2]
        gest = gestores[idx_c % 3]

        # ── Define status e histórico ─────────────────────────────────────────
        status_map = {
            "novo"             : StatusCandidatura.NOVO,
            "triagem_pendente" : StatusCandidatura.TRIAGEM_PENDENTE,
            "reprovado_triagem": StatusCandidatura.REPROVADO_TRIAGEM,
            "aprovado_triagem" : StatusCandidatura.APROVADO_TRIAGEM,
            "contratada"       : StatusCandidatura.CONTRATADO,
            "contratado"       : StatusCandidatura.CONTRATADO,
            "nao_aprovado"     : StatusCandidatura.NAO_APROVADO,
            "banco_talentos"   : StatusCandidatura.BANCO_TALENTOS,
            "rh_agendada"      : StatusCandidatura.ENTREVISTA_RH_AGENDADA,
            "rh_realizada"     : StatusCandidatura.ENTREVISTA_RH_REALIZADA,
            "tec_agendada"     : StatusCandidatura.ENTREVISTA_TEC_AGENDADA,
            "tec_realizada"    : StatusCandidatura.ENTREVISTA_TEC_REALIZADA,
            "decisao_pendente" : StatusCandidatura.DECISAO_PENDENTE,
        }
        status = status_map[etapa]

        # ── Monta histórico coerente ──────────────────────────────────────────
        historico = []
        passos = [
            ("novo", "aguardando_processamento", "sistema",  30),
            ("aguardando_processamento", "processando_curriculo", "sistema", 29),
            ("processando_curriculo", "triagem_pendente", "sistema", 28),
        ]
        if etapa not in ("novo",):
            for de, para, ator, dias in passos:
                historico.append({"de": de, "para": para, "ator": ator,
                                   "em": _ago(dias).isoformat()})

        if etapa in ("reprovado_triagem",):
            historico.append({"de":"triagem_pendente","para":"reprovado_triagem",
                               "ator":rh.nome,"em":_ago(20).isoformat()})
        elif etapa not in ("novo","triagem_pendente"):
            historico.append({"de":"triagem_pendente","para":"aprovado_triagem",
                               "ator":rh.nome,"em":_ago(20).isoformat()})

        if etapa in ("rh_agendada","rh_realizada","tec_agendada","tec_realizada",
                     "decisao_pendente","contratado","contratada","nao_aprovado","banco_talentos"):
            historico.append({"de":"aprovado_triagem","para":"entrevista_rh_agendada",
                               "ator":rh.nome,"em":_ago(15).isoformat()})

        if etapa in ("rh_realizada","tec_agendada","tec_realizada",
                     "decisao_pendente","contratado","contratada","nao_aprovado","banco_talentos"):
            historico.append({"de":"entrevista_rh_agendada","para":"entrevista_rh_realizada",
                               "ator":rh.nome,"em":_ago(10).isoformat()})

        if etapa in ("tec_agendada","tec_realizada","decisao_pendente",
                     "contratado","contratada","nao_aprovado","banco_talentos"):
            historico.append({"de":"entrevista_rh_realizada","para":"entrevista_tec_agendada",
                               "ator":gest.nome,"em":_ago(7).isoformat()})

        if etapa in ("tec_realizada","decisao_pendente","contratado","contratada",
                     "nao_aprovado","banco_talentos"):
            historico.append({"de":"entrevista_tec_agendada","para":"entrevista_tec_realizada",
                               "ator":gest.nome,"em":_ago(3).isoformat()})

        if etapa in ("decisao_pendente","contratado","contratada","nao_aprovado","banco_talentos"):
            historico.append({"de":"entrevista_tec_realizada","para":"decisao_pendente",
                               "ator":"sistema","em":_ago(2).isoformat()})

        final_map = {
            "contratado" :"contratado", "contratada":"contratado",
            "nao_aprovado":"nao_aprovado", "banco_talentos":"banco_de_talentos",
        }
        if etapa in final_map:
            historico.append({"de":"decisao_pendente","para":final_map[etapa],
                               "ator":rh.nome,"em":_ago(1).isoformat()})

        # Alguns candidatos simulam ter chegado via integração externa
        origem_ext = idx_c in (6, 7, 13, 22, 24)
        cand_obj = Candidatura(
            candidato_id=cand.id, vaga_id=vaga.id,
            status=status, historico=historico,
            origem="externo" if origem_ext else "manual",
            fonte="greenhouse" if origem_ext else None,
        )
        db.add(cand_obj)
        db.flush()

        # ── Currículo (para etapas após triagem) ─────────────────────────────
        s_cv = None
        precisa_curriculo = etapa not in ("novo",)
        if precisa_curriculo:
            s_rh, s_mkt, s_cv, expl = _score(cv, vaga)
            curriculo = Curriculo(
                candidatura_id=cand_obj.id,
                texto_extraido=cv,
                vetor_embedding=vetorizar_texto(cv),
                score_rh=s_rh,
                score_mercado=s_mkt,
                score_curriculo=s_cv,
                explicacao=expl,
                processado_em=_ago(28),
            )
            db.add(curriculo)

        # ── Entrevista RH ─────────────────────────────────────────────────────
        rh_score = None
        if etapa in ("rh_agendada","rh_realizada","tec_agendada","tec_realizada",
                     "decisao_pendente","contratado","contratada","nao_aprovado","banco_talentos"):
            nota_rh = NOTAS_RH[idx_c % len(NOTAS_RH)]
            rh_status = "realizada" if etapa != "rh_agendada" else "agendada"
            rh_score  = round(6.0 + (idx_c % 4) * 0.8, 1) if rh_status == "realizada" else None
            ent_rh = Entrevista(
                candidatura_id=cand_obj.id,
                entrevistador_id=rh.id,
                tipo="rh",
                status=rh_status,
                agendada_para=_ago(12) if rh_status == "realizada" else _daqui(3),
                realizada_em=_ago(10) if rh_status == "realizada" else None,
                score_manual=rh_score,
                anotacoes=nota_rh[0] if rh_status == "realizada" else None,
                pontos_fortes=nota_rh[1] if rh_status == "realizada" else None,
                pontos_fracos=nota_rh[2] if rh_status == "realizada" else None,
            )
            db.add(ent_rh)

        # ── Entrevista Técnica ────────────────────────────────────────────────
        tec_score = None
        if etapa in ("tec_agendada","tec_realizada","decisao_pendente",
                     "contratado","contratada","nao_aprovado","banco_talentos"):
            nota_tec = NOTAS_TEC[idx_c % len(NOTAS_TEC)]
            tec_status = "realizada" if etapa != "tec_agendada" else "agendada"
            tec_score  = round(7.0 + (idx_c % 3) * 0.5, 1) if tec_status == "realizada" else None

            historico_edicoes = []
            if tec_status == "realizada" and idx_c % 3 == 0:
                historico_edicoes = [{
                    "texto_anterior": "Avaliação inicial — pendente de complemento.",
                    "editado_em"    : _ago(2, horas=3).isoformat(),
                    "editado_por"   : gest.nome,
                }]

            ent_tec = Entrevista(
                candidatura_id=cand_obj.id,
                entrevistador_id=gest.id,
                tipo="tecnica",
                status=tec_status,
                agendada_para=_ago(5) if tec_status == "realizada" else _daqui(5),
                realizada_em=_ago(3) if tec_status == "realizada" else None,
                score_manual=tec_score,
                anotacoes=nota_tec[0] if tec_status == "realizada" else None,
                pontos_fortes=nota_tec[1] if tec_status == "realizada" else None,
                pontos_fracos=nota_tec[2] if tec_status == "realizada" else None,
                historico_edicoes=historico_edicoes,
            )
            db.add(ent_tec)

        # ── Scores consolidados na candidatura ───────────────────────────────
        if rh_score is not None:
            cand_obj.score_entrevista_rh = rh_score
        if tec_score is not None:
            cand_obj.score_entrevista_tec = tec_score
        if s_cv is not None:
            cand_obj.score_total = calcular_score_final(
                s_cv, rh_score, tec_score,
                vaga.peso_curriculo, vaga.peso_entrevista_rh, vaga.peso_entrevista_tec,
            )

        criadas.append(cand_obj)

    db.commit()
    return criadas


# ─────────────────────────────────────────────────────────────────────────────
def resumo(vagas, candidatos, candidaturas, usuarios):
    from collections import Counter
    contagem = Counter(c.status for c in candidaturas)
    print("\n" + "=" * 60)
    print("  BANCO POPULADO — RESUMO")
    print("=" * 60)
    print(f"\n  Vagas       : {len(vagas)}")
    print(f"  Candidatos  : {len(candidatos)}")
    print(f"  Candidaturas: {len(candidaturas)}")

    print("\n  Gestores por vaga:")
    gestores_por_id = {str(u.id): u.nome for u in usuarios.values()
                       if u.papel.value == "gestor"}
    for i, v in enumerate(vagas):
        nomes = [gestores_por_id.get(gid, gid) for gid in (v.gestores_ids or [])]
        print(f"  [{i}] {v.nome[:40]:<40} → {', '.join(nomes) if nomes else '(sem gestor)'}")

    print("\n  Distribuição do pipeline:")
    ordem = [
        StatusCandidatura.NOVO, StatusCandidatura.TRIAGEM_PENDENTE,
        StatusCandidatura.APROVADO_TRIAGEM, StatusCandidatura.REPROVADO_TRIAGEM,
        StatusCandidatura.ENTREVISTA_RH_AGENDADA, StatusCandidatura.ENTREVISTA_RH_REALIZADA,
        StatusCandidatura.ENTREVISTA_TEC_AGENDADA, StatusCandidatura.ENTREVISTA_TEC_REALIZADA,
        StatusCandidatura.DECISAO_PENDENTE, StatusCandidatura.CONTRATADO,
        StatusCandidatura.NAO_APROVADO, StatusCandidatura.BANCO_TALENTOS,
    ]
    for s in ordem:
        n = contagem.get(s, 0)
        if n:
            barra = "█" * n
            print(f"  {s.value:<35} {barra} {n}")

    print("\n  Logins:")
    print("  ana@sirs.com / bruno@sirs.com         → RH       (senha123)")
    print("  leitorairritada@gmail.com             → RH       (senha123)")
    print("  carlos / daniela / eduardo @sirs.com  → Gestor   (senha123)")
    print(f"  {settings.ADMIN_EMAIL:<40} → Admin    ({settings.ADMIN_SENHA})")
    print("\n  Candidata adicionada:")
    print("  juliaduran1515@gmail.com → triagem_pendente na vaga 'Desenvolvedor Python Sênior'")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nIniciando seed completo...")
    limpar()
    print("Criando usuários...")
    usuarios = criar_usuarios()
    print("Criando vagas e vetorizando requisitos...")
    vagas = criar_vagas(usuarios)
    print("Criando candidatos...")
    candidatos = criar_candidatos()
    print("Criando candidaturas, currículos e entrevistas (gerando embeddings)...")
    candidaturas = criar_candidaturas(vagas, candidatos, usuarios)
    resumo(vagas, candidatos, candidaturas, usuarios)
    db.close()
