import httpx
import numpy as np
from collections import Counter
from app.core.config import settings
from app.ai.resume_parser import get_model, vetorizar_texto

import re
import numpy as np
from collections import Counter
import httpx
from app.core.config import settings
from app.ai.resume_parser import get_model

# Organizada por categoria — fácil de expandir
SKILLS_REFERENCIA = {
    # Linguagens
    "python", "java", "javascript", "typescript", "go", "golang",
    "rust", "scala", "kotlin", "swift", "ruby", "php", "c++", "c#",
    "r", "matlab", "bash", "shell", "perl", "dart", "flutter",

    # Web / Backend
    "fastapi", "django", "flask", "spring", "spring boot", "node.js",
    "nodejs", "express", "nestjs", "laravel", "rails", "asp.net",
    "graphql", "rest", "grpc", "websocket",

    # Frontend
    "react", "vue", "angular", "next.js", "nextjs", "nuxt",
    "html", "css", "tailwind", "sass", "webpack", "vite",

    # Banco de dados
    "postgresql", "postgres", "mysql", "mongodb", "redis",
    "elasticsearch", "cassandra", "dynamodb", "sqlite", "oracle",
    "sql server", "sqlserver", "mariadb", "neo4j", "influxdb",

    # Cloud
    "aws", "amazon web services", "gcp", "google cloud", "azure",
    "heroku", "vercel", "cloudflare", "digital ocean",

    # DevOps / Infra
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "github actions", "gitlab ci", "ci/cd", "linux", "nginx",
    "prometheus", "grafana", "datadog", "helm",

    # Dados / IA
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "spark", "airflow", "kafka", "dbt", "power bi", "tableau",
    "looker", "bigquery", "snowflake", "databricks", "mlflow",

    # Práticas
    "git", "agile", "scrum", "kanban", "tdd", "solid",
    "microservices", "microsserviços", "api rest", "clean code",
    "domain driven design", "ddd", "event driven",

    # RH
    "esocial", "clt", "workday", "sap hcm", "success factors",
    "gupy", "people analytics",

    # Direito
    "oab", "irpj", "csll", "pis", "cofins", "planejamento fiscal",
    "direito tributário", "direito trabalhista", "compliance", "lgpd",

    # Engenharia Civil
    "autocad", "revit", "bim", "crea", "sinapi", "ms project",
    "primavera", "sketchup", "qgis",

    # Soft skills relevantes
    "liderança", "comunicação", "gestão de projetos",
    "resolução de problemas", "trabalho em equipe",
    "inglês", "english", "espanhol", "spanish",
}


def extrair_skills_por_referencia(textos: list[str]) -> list[tuple[str, int]]:
    """
    Abordagem muito mais precisa: verifica quais skills da lista
    de referência aparecem nos textos.
    Funciona bem com o campo skills_desc do LinkedIn.
    """
    contador = Counter()

    for texto in textos:
        texto_lower = texto.lower()

        for skill in SKILLS_REFERENCIA:
            # busca a skill como palavra completa (não substring)
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, texto_lower):
                contador[skill] += 1

    return contador.most_common(30)


def extrair_termos_frequentes(textos: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """
    Trata o skills_desc do LinkedIn que vem como:
    'Python,FastAPI,PostgreSQL,Docker,AWS'
    Cada item já é uma skill — só precisa contar.
    """
    contador = Counter()

    for texto in textos:
        # Divide por vírgula — cada item é uma skill
        skills = [s.strip().lower() for s in texto.split(",")]

        for skill in skills:
            # Remove espaços extras e caracteres especiais
            skill = skill.strip(" \t\n\r\"'")

            # Ignora muito curto ou vazio
            if len(skill) < 2:
                continue

            # Ignora stopwords genéricas
            if skill in {
                "and", "the", "or", "a", "an", "in", "of", "to",
                "with", "for", "is", "are", "be", "been", "being",
                "ability", "support", "management", "solutions",
                "technical", "customer", "applications", "design",
                "technology", "developing", "testing", "systems",
                "services", "service", "using", "tools", "various",
            }:
                continue

            contador[skill] += 1

    return contador.most_common(top_n)


# ── Coletor Adzuna ─────────────────────────────────────────────────────────
async def coletar_adzuna(titulo_vaga: str, n_paginas: int = 2) -> list[str]:
    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
        raise ValueError("Configure ADZUNA_APP_ID e ADZUNA_APP_KEY no .env.")

    textos   = []
    base_url = f"https://api.adzuna.com/v1/api/jobs/{settings.ADZUNA_COUNTRY}/search"

    async with httpx.AsyncClient(timeout=30) as client:
        for pagina in range(1, n_paginas + 1):
            url = f"{base_url}/{pagina}"
            response = await client.get(url, params={
                "app_id"          : settings.ADZUNA_APP_ID,
                "app_key"         : settings.ADZUNA_APP_KEY,
                "what"            : titulo_vaga,
                "where"           : "Brasil",     # ← filtra por Brasil
                "results_per_page": 20,
                "content-type"    : "application/json",
            })

            if response.status_code != 200:
                print(f"Adzuna erro {response.status_code} na página {pagina}")
                break

            dados = response.json()
            vagas = dados.get("results", [])

            if not vagas:
                break

            for vaga in vagas:
                descricao = vaga.get("description", "")
                titulo    = vaga.get("title", "")
                if descricao:
                    textos.append(f"{titulo}. {descricao}")

    print(f"Adzuna: {len(textos)} vagas coletadas para '{titulo_vaga}'")
    return textos


# Mapeamento de termos em português → termos em inglês para busca no LinkedIn
MAPEAMENTO_CARGOS = {
    # Tecnologia
    "python"              : "python",
    "desenvolvedor"       : "software engineer",
    "desenvolvimento"     : "software engineer",
    "engenheiro"          : "engineer",
    "frontend"            : "frontend",
    "backend"             : "backend",
    "fullstack"           : "full stack",
    "dados"               : "data",
    "ciência de dados"    : "data scientist",
    "cientista"           : "data scientist",
    "machine learning"    : "machine learning",
    "devops"              : "devops",
    "infraestrutura"      : "infrastructure",
    "segurança"           : "security",
    "mobile"              : "mobile",
    "arquiteto"           : "architect",

    # RH
    "recursos humanos"    : "human resources",
    "recrutamento"        : "recruiter",
    "seleção"             : "talent acquisition",
    "treinamento"         : "learning development",
    "rh"                  : "human resources",
    "people"              : "human resources",

    # Direito
    "advogado"            : "attorney lawyer",
    "advocacia"           : "attorney",
    "jurídico"            : "legal",
    "tributário"          : "tax",
    "trabalhista"         : "employment law",
    "compliance"          : "compliance",

    # Engenharia Civil
    "engenharia civil"    : "civil engineer",
    "obras"               : "construction",
    "infraestrutura civil": "civil infrastructure",
    "estruturas"          : "structural engineer",

    # Gestão
    "gerente"             : "manager",
    "gestão"              : "management",
    "coordenador"         : "coordinator",
    "analista"            : "analyst",
    "consultor"           : "consultant",
    "diretor"             : "director",

    # Dados / BI
    "business intelligence": "business intelligence",
    "analista de dados"   : "data analyst",
    "engenheiro de dados" : "data engineer",

    # Marketing
    "marketing"           : "marketing",
    "growth"              : "growth",
    "produto"             : "product manager",
    "ux"                  : "ux designer",
    "design"              : "designer",
}


def traduzir_cargo(titulo_vaga: str) -> str:
    """
    Traduz o título da vaga para inglês para buscar no dataset do LinkedIn.
    Usa mapeamento por palavras-chave — sem dependência externa.
    """
    titulo_lower = titulo_vaga.lower()
    termos_encontrados = []

    # Verifica primeiro frases compostas (maior match primeiro)
    mapeamentos_ordenados = sorted(
        MAPEAMENTO_CARGOS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for pt, en in mapeamentos_ordenados:
        if pt in titulo_lower:
            termos_encontrados.append(en)
            # Remove o termo encontrado para não duplicar
            titulo_lower = titulo_lower.replace(pt, "")

    if termos_encontrados:
        resultado = " ".join(termos_encontrados[:2])  # máximo 2 termos
        print(f"Tradução: '{titulo_vaga}' → '{resultado}'")
        return resultado

    # Se não encontrou mapeamento, usa o título original
    # (pode ser um termo técnico universal como "Python", "React")
    print(f"Sem mapeamento: usando '{titulo_vaga}' diretamente")
    return titulo_vaga


def coletar_kaggle(titulo_vaga: str) -> list[str]:
    import pandas as pd
    import os

    caminho = "/app/data/postings.csv"

    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Dataset não encontrado em {caminho}")

    df = pd.read_csv(
        caminho,
        usecols=["title", "skills_desc"],
        low_memory=False
    )

    df = df.dropna(subset=["skills_desc"])
    df = df[df["skills_desc"].str.strip() != ""]

    # Traduz o título para inglês antes de buscar
    titulo_en = traduzir_cargo(titulo_vaga)
    palavras  = titulo_en.lower().split()

    # Busca pela palavra mais específica (geralmente a mais longa)
    palavras_uteis = [p for p in palavras if len(p) >= 4]
    palavras_uteis.sort(key=len, reverse=True)

    melhor_df = pd.DataFrame()
    for palavra in palavras_uteis:
        mask = df["title"].fillna("").str.lower().str.contains(
            palavra, regex=False
        )
        candidato = df[mask]
        if len(candidato) > len(melhor_df):
            melhor_df = candidato
            print(f"  '{palavra}' → {len(candidato)} vagas")

    if len(melhor_df) < 30:
        print(f"Poucas vagas ({len(melhor_df)}) — ampliando busca")
        # Busca por qualquer palavra técnica no skills_desc
        for palavra in palavras_uteis:
            mask = df["skills_desc"].fillna("").str.lower().str.contains(
                palavra, regex=False
            )
            candidato = df[mask]
            if len(candidato) > len(melhor_df):
                melhor_df = candidato
                print(f"  skills_desc '{palavra}' → {len(candidato)} vagas")

    textos = melhor_df["skills_desc"].head(300).tolist()
    print(f"Kaggle: {len(textos)} vagas para '{titulo_vaga}'")
    return textos

# ── Geração do vetor de mercado ────────────────────────────────────────────

def gerar_vetor_mercado(termos_frequentes: list[tuple[str, int]]) -> list[float]:
    """
    Vetoriza os top termos e gera um vetor médio ponderado pela frequência.
    Esse vetor representa semanticamente o que o mercado mais exige.
    """
    if not termos_frequentes:
        raise ValueError("Nenhum termo encontrado para gerar o vetor de mercado")

    model  = get_model()
    termos = [t[0] for t in termos_frequentes]
    pesos  = np.array([t[1] for t in termos_frequentes], dtype=float)
    pesos  = pesos / pesos.sum()  # normaliza para soma 1.0

    # vetoriza todos os termos de uma vez
    vecs = model.encode(
        termos,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # média ponderada pela frequência
    vetor_mercado = np.average(vecs, axis=0, weights=pesos)
    vetor_mercado = vetor_mercado / np.linalg.norm(vetor_mercado)

    return vetor_mercado.tolist()


# ── Pipeline completo ──────────────────────────────────────────────────────

async def analisar_mercado(titulo_vaga: str) -> dict:
    """
    Pipeline completo: coleta vagas → extrai termos → gera vetor.
    Retorna o vetor de mercado e os top termos para exibir no dashboard.
    """
    source = settings.MARKET_ANALYZER_SOURCE

    # 1. Coleta vagas do mercado
    if source == "adzuna":
        textos = await coletar_adzuna(titulo_vaga)
    elif source == "kaggle":
        textos = coletar_kaggle(titulo_vaga)
    else:
        raise ValueError(f"Fonte inválida: {source}. Use 'adzuna' ou 'kaggle'")

    if not textos:
        raise ValueError(f"Nenhuma vaga encontrada para '{titulo_vaga}'")

    # 2. Extrai termos mais frequentes
    termos_frequentes = extrair_termos_frequentes(textos, top_n=30)
    print(f"Top 10 termos: {termos_frequentes[:10]}")

    # 3. Gera o vetor de mercado
    vetor = gerar_vetor_mercado(termos_frequentes)

    return {
        "vetor_mercado"    : vetor,
        "termos_frequentes": [
            {"termo": t, "frequencia": f}
            for t, f in termos_frequentes[:20]
        ],
        "total_vagas_analisadas": len(textos),
        "fonte": source,
    }