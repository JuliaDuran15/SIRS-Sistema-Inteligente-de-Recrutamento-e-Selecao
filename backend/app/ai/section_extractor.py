"""
Segmentação de currículo em seções temáticas.

Estratégia em duas etapas:
  1. Detecção por cabeçalho: linhas curtas em maiúsculas ou que batem com
     padrões conhecidos (EXPERIÊNCIA, HABILIDADES, FORMAÇÃO, RESUMO).
  2. Fallback por densidade semântica: para CVs sem cabeçalhos, busca
     parágrafos com alta concentração de termos característicos de cada seção.

Retorna um dict com o texto de cada seção (string vazia quando não detectada).
"""
import re
from typing import Literal

SecaoNome = Literal["experiencia", "habilidades", "educacao", "resumo"]

# ── Padrões de cabeçalho por seção ───────────────────────────────────────────
_CABECALHOS: dict[SecaoNome, list[str]] = {
    "experiencia": [
        r"experi[eê]ncia\s*profissional",
        r"hist[oó]rico\s+profissional",
        r"trajet[oó]ria\s+profissional",
        r"experi[eê]ncia",
        r"work\s+experience",
        r"professional\s+experience",
        r"employment\s+history",
    ],
    "habilidades": [
        r"habilidades\s+t[eé]cnicas",
        r"compet[eê]ncias\s+t[eé]cnicas",
        r"conhecimentos\s+t[eé]cnicos",
        r"habilidades",
        r"compet[eê]ncias",
        r"tecnologias",
        r"skills",
        r"stack\s+tecnol[oó]gico",
    ],
    "educacao": [
        r"forma[cç][aã]o\s+acad[eê]mica",
        r"hist[oó]rico\s+acad[eê]mico",
        r"forma[cç][aã]o",
        r"educa[cç][aã]o",
        r"gradua[cç][aã]o",
        r"education",
        r"academic\s+background",
    ],
    "resumo": [
        r"resumo\s+profissional",
        r"resumo\s+executivo",
        r"sobre\s+mim",
        r"perfil\s+profissional",
        r"perfil",
        r"objetivo\s+profissional",
        r"objetivo",
        r"summary",
        r"profile",
        r"about\s+me",
    ],
}

# Palavras-chave de fallback (para CVs sem cabeçalhos explícitos)
_KEYWORDS_FALLBACK: dict[SecaoNome, list[str]] = {
    "experiencia": [
        "responsável", "desenvolvi", "trabalhei", "atuei", "liderou",
        "implementou", "gerenciei", "coordenei", "empresa", "cargo", "função",
        "managed", "developed", "led", "responsible",
    ],
    "habilidades": [
        "python", "java", "docker", "kubernetes", "aws", "react", "sql",
        "fastapi", "django", "spring", "node", "typescript", "git",
        "linux", "bash", "tensorflow", "spark", "kafka",
    ],
    "educacao": [
        "universidade", "faculdade", "graduação", "bacharelado", "mestrado",
        "doutorado", "mba", "curso", "certificado", "formado",
        "university", "bachelor", "master", "degree",
    ],
    "resumo": [
        "profissional com", "especialista em", "experiência em", "anos de",
        "apaixonado", "focado em", "buscando",
        "professional with", "specializing in",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────

def extrair_secoes(texto: str) -> dict[SecaoNome, str]:
    """
    Segmenta o texto do currículo em seções e retorna um dict.
    Seções não detectadas retornam string vazia.
    """
    linhas = [linha.rstrip() for linha in texto.splitlines()]
    secoes = _segmentar_por_cabecalho(linhas)

    # Fallback: seções não encontradas → varredura por densidade
    secoes_vazias = [s for s, t in secoes.items() if not t.strip()]
    if secoes_vazias:
        secoes_fallback = _segmentar_por_densidade(texto, secoes_vazias)
        for s in secoes_vazias:
            if secoes_fallback.get(s):
                secoes[s] = secoes_fallback[s]

    return secoes


def texto_para_rerank(texto: str, max_chars: int = 800) -> str:
    """
    Extrai o trecho mais relevante do currículo para o cross-encoder.
    Preferência: resumo + experiência. Limita a max_chars para caber no
    token limit do modelo (512 tokens ≈ 1800–2000 chars, usamos 800 para
    deixar espaço para o texto da vaga no par (vaga, cv)).
    """
    secoes = extrair_secoes(texto)
    partes = []
    for nome in ("resumo", "experiencia", "habilidades"):
        t = secoes.get(nome, "").strip()
        if t:
            partes.append(t)
    candidato = " ".join(partes) if partes else texto
    return candidato[:max_chars]


# ── Helpers internos ──────────────────────────────────────────────────────────

def _e_cabecalho(linha: str) -> SecaoNome | None:
    """Detecta se uma linha é um cabeçalho de seção e retorna o nome da seção."""
    s = linha.strip()
    if not s or len(s) > 60:          # cabeçalhos são curtos
        return None

    s_lower = s.lower()

    # Heurística: pode ser cabeçalho se for todo maiúsculo OU terminar com ":"
    # OU bater com um padrão conhecido
    parece_cabecalho = s.isupper() or s.endswith(":") or len(s.split()) <= 5

    for secao, padroes in _CABECALHOS.items():
        for p in padroes:
            if re.fullmatch(p + r"[:\s]*", s_lower):
                return secao  # type: ignore
            if parece_cabecalho and re.search(p, s_lower):
                return secao  # type: ignore

    return None


def _segmentar_por_cabecalho(
    linhas: list[str],
) -> dict[SecaoNome, str]:
    secoes: dict[SecaoNome, list[str]] = {
        "experiencia": [], "habilidades": [], "educacao": [], "resumo": [],
    }
    secao_atual: SecaoNome | None = None

    for linha in linhas:
        nova = _e_cabecalho(linha)
        if nova:
            secao_atual = nova
            continue
        if secao_atual and linha.strip():
            secoes[secao_atual].append(linha)

    return {k: "\n".join(v) for k, v in secoes.items()}


def _segmentar_por_densidade(
    texto: str,
    secoes_alvo: list[SecaoNome],
) -> dict[SecaoNome, str]:
    """
    Para CVs sem cabeçalhos, divide o texto em parágrafos e atribui cada
    parágrafo à seção com maior densidade de palavras-chave.
    """
    paragrafos = [p.strip() for p in re.split(r"\n{2,}", texto) if p.strip()]
    if not paragrafos:
        return {s: "" for s in secoes_alvo}

    atribuicoes: dict[SecaoNome, list[str]] = {s: [] for s in secoes_alvo}

    for paragrafo in paragrafos:
        p_lower = paragrafo.lower()
        melhor_secao: SecaoNome | None = None
        melhor_score = 0

        for secao in secoes_alvo:
            score = sum(1 for kw in _KEYWORDS_FALLBACK[secao] if kw in p_lower)
            if score > melhor_score:
                melhor_score = score
                melhor_secao = secao  # type: ignore

        if melhor_secao and melhor_score > 0:
            atribuicoes[melhor_secao].append(paragrafo)

    return {s: "\n\n".join(ps) for s, ps in atribuicoes.items()}
