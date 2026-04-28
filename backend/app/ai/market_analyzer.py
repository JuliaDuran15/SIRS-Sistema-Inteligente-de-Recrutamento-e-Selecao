import math
import re
from collections import Counter

import httpx
import numpy as np
from app.ai.resume_parser import get_model
from app.core.config import settings

# ── Tradução ───────────────────────────────────────────────────────────────

def traduzir_para_ingles(texto: str) -> str:
    """Traduz texto para inglês usando deep-translator (sem API key)."""
    try:
        from deep_translator import GoogleTranslator
        traduzido = GoogleTranslator(source="auto", target="en").translate(texto)
        print(f"Tradução: '{texto}' → '{traduzido}'")
        return traduzido
    except Exception as e:
        print(f"Tradução falhou ({e}) — usando original")
        return texto


def traduzir_para_portugues(texto: str) -> str:
    """Traduz texto para português usando deep-translator."""
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target="pt").translate(texto)
    except Exception:
        return texto


# ── Skills de referência ───────────────────────────────────────────────────

CATEGORIAS_CARGO = {
    "tech"            : {"fonte": "kaggle"},
    "direito"         : {"fonte": "adzuna"},
    "rh"              : {"fonte": "adzuna"},
    "engenharia_civil": {"fonte": "adzuna"},
    "engenharia_geral": {"fonte": "adzuna"},
    "saude"           : {"fonte": "adzuna"},
    "financeiro"      : {"fonte": "adzuna"},
    "marketing"       : {"fonte": "adzuna"},
}

# Skills curadas por categoria — usadas quando as fontes retornam pouco
SKILLS_CURADAS = {
    "tech": [
        ("python", 100), ("aws", 90), ("docker", 85), ("postgresql", 80),
        ("javascript", 80), ("kubernetes", 75), ("react", 70), ("git", 70),
        ("linux", 65), ("ci/cd", 65), ("microservices", 60), ("redis", 55),
    ],
    "direito": [
        ("oab", 100), ("direito tributário", 90), ("direito trabalhista", 85),
        ("compliance", 80), ("lgpd", 75), ("contencioso", 70),
        ("planejamento fiscal", 70), ("irpj", 65), ("csll", 60),
        ("contratos", 60), ("litigation", 55), ("legal research", 55),
    ],
    "rh": [
        ("recrutamento e seleção", 100), ("esocial", 90), ("clt", 85),
        ("people analytics", 80), ("treinamento", 75), ("onboarding", 70),
        ("avaliação de desempenho", 70), ("workday", 60), ("sap hcm", 55),
        ("excel", 55), ("entrevista por competências", 50),
    ],
    "engenharia_civil": [
        ("autocad", 100), ("revit", 90), ("bim", 85), ("ms project", 80),
        ("sinapi", 75), ("crea", 75), ("gestão de obras", 70),
        ("orçamento", 65), ("nr-18", 60), ("topografia", 55),
        ("sketchup", 50), ("primavera", 50), ("qgis", 45),
    ],
        "engenharia_geral": [
        ("autocad", 100), ("excel", 90), ("gestão de projetos", 85),
        ("normas técnicas", 80), ("crea", 75), ("abnt", 70),
        ("iso 9001", 65), ("lean", 60), ("six sigma", 60),
        ("engenharia de processos", 55), ("segurança do trabalho", 55),
        ("manutenção", 50), ("qualidade", 50),
    ],
    "saude": [
        ("prontuário eletrônico", 100), ("cfm", 90), ("coren", 85),
        ("bls", 80), ("acls", 75), ("sus", 70), ("anvisa", 65),
        ("farmacologia", 60), ("diagnóstico", 60), ("cirurgia", 55),
        ("atendimento ao paciente", 55), ("excel", 50),
    ],
    "financeiro": [
        ("excel avançado", 100), ("sap", 90), ("controladoria", 85),
        ("ifrs", 80), ("cpc", 75), ("crc", 70), ("power bi", 70),
        ("fluxo de caixa", 65), ("conciliação", 60), ("totvs", 60),
        ("planejamento financeiro", 55), ("auditoria", 55),
    ],
    "marketing": [
        ("google analytics", 100), ("meta ads", 90), ("seo", 85),
        ("google ads", 80), ("social media", 75), ("crm", 70),
        ("hubspot", 65), ("email marketing", 65), ("figma", 60),
        ("copywriting", 60), ("growth hacking", 55), ("excel", 50),
    ],
}


def detectar_categoria(titulo_vaga: str) -> str:
    """Detecta a categoria normalizando acentos."""
    import unicodedata

    def normalizar(texto: str) -> str:
        return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()

    titulo_norm = normalizar(titulo_vaga)

    # Mapeamento normalizado
    CATEGORIAS_NORM = {
        "tech"            : {"python", "java", "javascript", "developer",
                             "desenvolvedor", "software", "frontend", "backend",
                             "fullstack", "devops", "dados", "data",
                             "machine learning", "cloud", "mobile", "react",
                             "angular", "vue", "nodejs", "programador"},
        "direito"         : {"advogado", "juridico", "direito", "tributario",
                             "trabalhista", "attorney", "lawyer", "legal",
                             "compliance", "oab", "procurador", "defensor"},
        "rh"              : {"recursos humanos", "recrutamento", "selecao", "rh",
                             "people", "talent", "treinamento", "human resources",
                             "hr", "recruiter", "departamento pessoal", "dp"},
        "engenharia_civil": {"engenheiro civil", "engenharia civil",
                             "civil engineer", "obras", "construcao",
                             "estrutural", "geotecnia", "hidraulica",
                             "topografia", "pavimentacao", "saneamento"},
        "engenharia_geral": {"engenheiro", "engenharia", "engineer", "tecnico",
                             "quimico", "mecanico", "eletrico", "producao",
                             "ambiental", "chemical", "mechanical", "electrical"},
        "saude"           : {"medico", "medicina", "enfermeiro", "enfermagem",
                             "farmaceutico", "fisioterapeuta", "nutricionista",
                             "psicologo", "dentista", "veterinario", "biomedico",
                             "radiologista", "saude", "clinico", "cirurgiao",
                             "pediatra", "cardiologista", "neurologista"},
        "financeiro"      : {"contador", "contabilidade", "financeiro",
                             "controladoria", "auditoria", "fiscal",
                             "tesouraria", "controller", "financas"},
        "marketing"       : {"marketing", "publicidade", "comunicacao",
                             "social media", "designer", "redator",
                             "copywriter", "growth", "seo", "midia",
                             "branding", "produto"},
    }

    for categoria, palavras in CATEGORIAS_NORM.items():
        for palavra in palavras:
            if normalizar(palavra) in titulo_norm:
                print(f"Categoria detectada: {categoria}")
                return categoria

    print("Categoria: tech (padrão)")
    return "tech"

# ── Extração de skills ─────────────────────────────────────────────────────

def limpar_skills_desc(texto: str) -> list[str]:
    """
    Processa o skills_desc do LinkedIn.
    Pode vir como:
    - "Python,Docker,AWS" (lista limpa)
    - "Python, Docker, AWS" (com espaços)
    - Texto corrido com frases longas
    """
    # Divide por vírgula
    partes = [p.strip() for p in texto.split(",")]

    skills_limpas = []
    for parte in partes:
        # Ignora frases longas (texto corrido, não skill)
        if len(parte) > 50:
            continue
        # Ignora muito curto
        if len(parte) < 2:
            continue
        # Ignora se começa com artigo/pronome (texto corrido)
        primeira_palavra = parte.split()[0].lower() if parte.split() else ""
        if primeira_palavra in {"we", "our", "this", "the", "a", "an", "at", "and"}:
            continue

        skills_limpas.append(parte.lower().strip())

    return skills_limpas

def extrair_de_adzuna(textos: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """
    Extração com TF-IDF simplificado:
    - TF: frequência do termo naquele conjunto de vagas
    - IDF: penaliza termos que aparecem em todas as vagas (genéricos)
    """

    SKILLS_POR_DOMINIO = {
        # Tech
        "python", "java", "javascript", "typescript", "react", "angular",
        "vue", "nodejs", "django", "fastapi", "flask", "spring",
        "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
        "aws", "azure", "gcp", "terraform", "linux", "git", "ci/cd",
        "microservices", "agile", "scrum", "devops", "machine learning",
        "sql", "excel", "power bi", "tableau", "spark", "airflow",
        "typescript", "kotlin", "swift", "golang", "rust",

        # RH — específicos
        "recrutamento e seleção", "people analytics", "workday", "sap hcm",
        "success factors", "gupy", "onboarding", "offboarding",
        "avaliação de desempenho", "entrevista por competências",
        "mapeamento de competências", "dhp", "pcd",

        # Direito — específicos
        "oab", "direito tributário", "direito trabalhista", "compliance",
        "lgpd", "irpj", "csll", "pis", "cofins", "planejamento fiscal",
        "contencioso", "processo civil", "processo penal", "arbitragem",
        "peticionamento", "habeas corpus", "mandado de segurança",
        "pje", "e-saj", "tjsp", "stj", "stf",

        # Engenharia Civil — específicos
        "autocad", "revit", "bim", "ms project", "sinapi", "crea",
        "gestão de obras", "topografia", "nr-18", "sketchup",
        "primavera", "qgis", "projetos estruturais", "fundações",
        "hidráulica", "saneamento", "pavimentação", "laudo técnico",

        # Engenharia Geral — específicos
        "iso 9001", "lean", "six sigma", "kaizen", "fmea",
        "engenharia de processos", "manutenção preventiva",
        "manutenção preditiva", "pcp", "chão de fábrica",
        "autocad", "solidworks", "ansys", "matlab",

        # Saúde — específicos
        "crm", "coren", "crf", "cfm", "sus", "anvisa", "bls", "acls",
        "prontuário eletrônico", "tasy", "mvtech", "totvs saúde",
        "farmacologia", "diagnóstico clínico", "cirurgia",

        # Financeiro — específicos
        "ifrs", "cpc", "crc", "totvs", "sap fi", "power bi",
        "fluxo de caixa", "conciliação bancária", "dre",
        "planejamento financeiro", "auditoria interna", "controladoria",

        # Marketing — específicos
        "google analytics", "meta ads", "google ads", "seo", "sem",
        "hubspot", "rdstation", "mailchimp", "figma", "adobe",
        "copywriting", "growth hacking", "crm", "salesforce",

        # Geral (aparecem em muitos cargos — peso menor)
        "inglês", "espanhol", "excel", "word", "powerpoint",
        "liderança", "comunicação", "gestão de projetos", "negociação",
        "pacote office", "sap",
    }

    # Termos que aparecem em QUALQUER vaga — ignorar completamente
    TERMOS_GENERICOS = {
        "clt", "benefícios", "recursos", "seleção", "recrutamento",
        "folha de pagamento", "vale transporte", "vale refeição",
        "plano de saúde", "plano odontológico", "férias", "13º",
        "carteira assinada", "regime clt", "pj", "mei",
        "esocial", "fgts", "inss", "holerite", "rescisão", "negociação",
    }

    # Conta em quantas vagas cada skill aparece (para IDF)
    doc_freq    = Counter()
    skill_por_doc = []
    n_docs      = len(textos)

    for texto in textos:
        texto_lower = texto.lower()
        skills_nesse_doc = set()

        for skill in SKILLS_POR_DOMINIO:
            if skill in TERMOS_GENERICOS:
                continue
            if re.search(r'\b' + re.escape(skill) + r'\b', texto_lower):
                skills_nesse_doc.add(skill)

        skill_por_doc.append(skills_nesse_doc)
        for skill in skills_nesse_doc:
            doc_freq[skill] += 1

    # Calcula TF-IDF simplificado
    scores = Counter()
    for skills in skill_por_doc:
        for skill in skills:
            tf  = 1
            idf = math.log(n_docs / (1 + doc_freq[skill]))
            # IDF alto = skill específica (aparece em poucas vagas)
            # IDF baixo = skill genérica (aparece em muitas vagas)
            scores[skill] += tf * idf

    # Converte para inteiros para compatibilidade
    resultado = [(skill, int(score * 10)) for skill, score in scores.most_common(top_n)]
    return resultado


def extrair_de_kaggle(textos: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """
    Extrai skills do formato LinkedIn (lista separada por vírgula).
    """
    contador = Counter()

    stopwords = {
        "and", "the", "or", "a", "an", "in", "of", "to", "with",
        "for", "is", "are", "be", "been", "ability", "support",
        "management", "solutions", "technical", "customer",
        "applications", "design", "technology", "developing",
        "testing", "systems", "services", "service", "using",
        "tools", "various", "experience", "knowledge", "skills",
        "strong", "work", "working", "role", "team", "business",
        "including", "communication", "verbal", "written",
    }

    for texto in textos:
        skills = limpar_skills_desc(texto)
        for skill in skills:
            if skill not in stopwords and len(skill) > 2:
                contador[skill] += 1

    return contador.most_common(top_n)


def extrair_termos_frequentes(textos: list[str], top_n: int = 30,
                               fonte: str = "kaggle") -> list[tuple[str, int]]:
    """Router — escolhe o extrator correto pela fonte."""
    if fonte == "adzuna":
        return extrair_de_adzuna(textos, top_n)
    return extrair_de_kaggle(textos, top_n)

# ── Coletor Kaggle ─────────────────────────────────────────────────────────

def coletar_kaggle(titulo_vaga: str) -> list[str]:
    import os

    import pandas as pd

    caminho = "/app/data/postings.csv"
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Dataset não encontrado em {caminho}")

    df = pd.read_csv(caminho, usecols=["title", "skills_desc"], low_memory=False)
    df = df.dropna(subset=["skills_desc"])
    df = df[df["skills_desc"].str.strip() != ""]

    # Traduz o título para inglês
    titulo_en = traduzir_para_ingles(titulo_vaga)

    # Remove palavras genéricas que poluem a busca
    palavras_ignorar = {
        "senior", "junior", "pleno", "mid", "level", "lead",
        "sênior", "specialist", "associate", "staff","clt"
    }
    palavras = [
        p for p in titulo_en.lower().split()
        if len(p) >= 4 and p not in palavras_ignorar
    ]
    palavras.sort(key=len, reverse=True)

    if not palavras:
        raise ValueError(f"Nenhum termo útil extraído de '{titulo_vaga}'")

    # Busca progressiva no título
    melhor_df = pd.DataFrame(columns=["title", "skills_desc"])
    for palavra in palavras:
        mask      = df["title"].fillna("").str.lower().str.contains(palavra, regex=False)
        candidato = df[mask]
        print(f"  '{palavra}' → {len(candidato)} vagas no título")
        if len(candidato) > len(melhor_df):
            melhor_df = candidato

    # Se ainda pouco, busca no skills_desc
    if len(melhor_df) < 30:
        for palavra in palavras:
            mask      = df["skills_desc"].fillna("").str.lower().str.contains(palavra, regex=False)
            candidato = df[mask]
            print(f"  skills '{palavra}' → {len(candidato)} vagas")
            if len(candidato) > len(melhor_df):
                melhor_df = candidato

    # Se ainda vazio, retorna lista vazia com mensagem clara
    if len(melhor_df) == 0:
        print(f"Nenhuma vaga encontrada para '{titulo_vaga}' no Kaggle")
        return []

    textos = melhor_df["skills_desc"].head(300).tolist()
    print(f"Kaggle: {len(textos)} vagas para '{titulo_vaga}'")
    return textos


# ── Coletor Adzuna ─────────────────────────────────────────────────────────

async def coletar_adzuna(titulo_vaga: str, n_paginas: int = 2) -> list[str]:
    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
        raise ValueError("Configure ADZUNA_APP_ID e ADZUNA_APP_KEY no .env.")

    textos   = []
    base_url = f"https://api.adzuna.com/v1/api/jobs/{settings.ADZUNA_COUNTRY}/search"

    async with httpx.AsyncClient(timeout=30) as client:
        for pagina in range(1, n_paginas + 1):
            url      = f"{base_url}/{pagina}"
            response = await client.get(url, params={
                "app_id"          : settings.ADZUNA_APP_ID,
                "app_key"         : settings.ADZUNA_APP_KEY,
                "what"            : titulo_vaga,
                "where"           : "Brasil",
                "results_per_page": 20,
            })

            if response.status_code != 200:
                break

            vagas = response.json().get("results", [])
            if not vagas:
                break

            for vaga in vagas:
                desc = vaga.get("description", "")
                if desc:
                    textos.append(vaga.get("title", "") + ". " + desc)

    print(f"Adzuna: {len(textos)} vagas para '{titulo_vaga}'")
    return textos


# ── Geração do vetor de mercado ────────────────────────────────────────────

def gerar_vetor_mercado(termos_frequentes: list[tuple[str, int]]) -> list[float]:
    if not termos_frequentes:
        raise ValueError("Nenhum termo para gerar vetor")

    model  = get_model()
    termos = [t[0] for t in termos_frequentes]
    pesos  = np.array([t[1] for t in termos_frequentes], dtype=float)
    pesos /= pesos.sum()

    # Traduz termos para português para comparação com currículos em PT
    termos_pt = []
    for t in termos:
        try:
            from deep_translator import GoogleTranslator
            pt = GoogleTranslator(source="auto", target="pt").translate(t)
            termos_pt.append(pt)
        except Exception:
            termos_pt.append(t)

    # Vetoriza em português para compatibilidade com currículos BR
    vecs          = model.encode(termos_pt, normalize_embeddings=True, show_progress_bar=False)
    vetor_mercado = np.average(vecs, axis=0, weights=pesos)
    vetor_mercado = vetor_mercado / np.linalg.norm(vetor_mercado)

    return vetor_mercado.tolist()


# ── Pipeline completo ──────────────────────────────────────────────────────
async def analisar_mercado(titulo_vaga: str) -> dict:
    source    = settings.MARKET_ANALYZER_SOURCE
    categoria = detectar_categoria(titulo_vaga)
    textos_adzuna = []
    textos_kaggle = []

    fonte_recomendada = CATEGORIAS_CARGO[categoria]["fonte"]
    usar_adzuna = source == "ambos" or fonte_recomendada == "adzuna"
    usar_kaggle = source == "ambos" or fonte_recomendada == "kaggle"

    if usar_adzuna:
        try:
            textos_adzuna = await coletar_adzuna(titulo_vaga)
        except Exception as e:
            print(f"Adzuna falhou: {e}")

    if usar_kaggle:
        try:
            textos_kaggle = coletar_kaggle(titulo_vaga)
        except Exception as e:
            print(f"Kaggle falhou: {e}")

    contador_final = Counter()

    if textos_adzuna:
        for termo, freq in extrair_de_adzuna(textos_adzuna, top_n=30):
            contador_final[termo] += freq * 2

    if textos_kaggle:
        for termo, freq in extrair_de_kaggle(textos_kaggle, top_n=30):
            contador_final[termo] += freq

    total = len(textos_adzuna) + len(textos_kaggle)

    # Usa curadas quando dados insuficientes (< 10 vagas)
    if total < 10 or not contador_final:
        print(f"Dados insuficientes ({total} vagas) — complementando com skills curadas")
        skills_curadas = SKILLS_CURADAS.get(categoria, SKILLS_CURADAS["tech"])
        # Mescla curadas com o que foi encontrado
        for termo, freq in skills_curadas:
            contador_final[termo] += freq

    termos_frequentes = contador_final.most_common(30)
    vetor             = gerar_vetor_mercado(termos_frequentes)

    return {
        "vetor_mercado"         : vetor,
        "termos_frequentes"     : [
            {"termo": t, "frequencia": f}
            for t, f in termos_frequentes[:20]
        ],
        "total_vagas_analisadas": total,
        "fonte"                 : fonte_recomendada if source != "ambos" else "ambos",
        "categoria"             : categoria,
    }