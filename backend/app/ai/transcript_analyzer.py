"""
Sumarização extrativa de transcrições de entrevistas.

Algoritmo:
  1. Limpa artefatos de transcrição (timestamps, labels de falante)
  2. Divide em sentenças
  3. Pontua relevância por TF-IDF
  4. Classifica cada sentença como forte / fraco / neutro por dicionário de keywords
  5. Retorna pontos_fortes, pontos_fracos e anotações (top sentenças neutras)
"""
import re
from collections import Counter
from math import log

# ─── Vocabulários de classificação (PT + EN) ──────────────────────────────────

_FORTES = {
    "liderança", "liderando", "liderou", "liderei", "gerenciei", "gerenciou",
    "coordenei", "coordenou", "desenvolvi", "desenvolveu", "implementei", "implementou",
    "criei", "criou", "entreguei", "entregou", "alcancei", "alcançou",
    "melhorei", "melhorou", "otimizei", "otimizou", "resolvi", "resolveu",
    "domínio", "dominio", "domina", "domino", "sólido", "sólida",
    "avançado", "avançada", "experiente", "forte", "excelente", "ótimo", "ótima",
    "fluente", "certificado", "certificada", "especialista", "especialização",
    "proativo", "proativa", "comunicação", "colaboração", "trabalho em equipe",
    "resultado", "impacto", "sucesso", "crescimento", "mentoria", "mentorei",
    "autonomia", "iniciativa", "entrega", "conquista", "reconhecimento",
    "led", "managed", "developed", "implemented", "delivered", "achieved",
    "improved", "optimized", "strong", "excellent", "expert", "fluent",
    "certified", "leadership", "teamwork", "proactive", "ownership",
}

_FRACOS = {
    "nunca trabalhei", "nunca usei", "não tenho", "não trabalhei", "não sei",
    "não conheço", "não domino", "pouco conhecimento",
    "básico", "básica", "superficial", "iniciante", "introdutório",
    "dificuldade", "dificuldades", "difícil", "desafiador",
    "fraqueza", "fraquezas", "fraco", "fraca", "limitado", "limitada",
    "aprendi recentemente", "estou aprendendo", "estudando ainda",
    "falta de", "faltou", "faltava",
    "problema", "problemas", "erro", "erros", "falha", "falhas",
    "conflito", "conflitos", "atraso", "atrasos",
    "preciso melhorar", "quero melhorar", "ainda não",
    "weakness", "weaknesses", "struggle", "struggled",
    "never", "lack", "limited", "basic", "beginner",
}

# ─── Pré-processamento ────────────────────────────────────────────────────────

def _limpar(texto: str) -> str:
    texto = re.sub(r'[\[\(]?\d{1,2}:\d{2}(?::\d{2})?[\]\)]?', '', texto)
    # Labels de falante: "Ana (RH):", "João:", "Entrevistador:" — com espaço opcional antes
    texto = re.sub(r'^\s*[A-ZÀ-Úa-zà-ú][A-Za-zÀ-ú ]{0,30}(?:\s*\([^)]{1,20}\))?\s*:\s*', '', texto, flags=re.MULTILINE)
    # Anotações de ruído sem dígitos: [inaudível], [risos], [ruído de fundo], (pausa)
    texto = re.sub(r'[\[\(][^\[\]\(\)\d]{1,30}[\]\)]', ' ', texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _sentencas(texto: str) -> list[str]:
    partes = re.split(r'(?<=[.!?])\s+|\n{2,}', texto)
    return [s.strip() for s in partes if len(s.strip()) > 20]


def _tokens(texto: str) -> list[str]:
    return re.findall(r'\b[a-zA-ZÀ-ú]{3,}\b', texto.lower())


# ─── TF-IDF ──────────────────────────────────────────────────────────────────

def _pontuar(sentencas: list[str]) -> list[float]:
    por_sent = [_tokens(s) for s in sentencas]
    N = max(len(sentencas), 1)

    df: Counter = Counter()
    for toks in por_sent:
        for t in set(toks):
            df[t] += 1

    scores = []
    for toks in por_sent:
        if not toks:
            scores.append(0.0)
            continue
        tf = Counter(toks)
        score = sum(
            (tf[t] / len(toks)) * log((N + 1) / (df[t] + 1))
            for t in tf if len(t) > 3
        )
        scores.append(score)
    return scores


# ─── Classificação e extração ─────────────────────────────────────────────────

def _classificar(sentenca: str) -> str:
    txt = sentenca.lower()
    pos = sum(1 for k in _FORTES if k in txt)
    neg = sum(1 for k in _FRACOS if k in txt)
    if pos > neg: return "forte"
    if neg > pos: return "fraco"
    return "neutro"


def _resumir(sentenca: str, max_len: int = 55) -> str:
    s = sentenca.strip().rstrip('.,;:!?')
    if len(s) <= max_len:
        return s
    return s[:max_len].rsplit(' ', 1)[0].rstrip('.,;:') + '…'


# ─── API pública ─────────────────────────────────────────────────────────────

def analisar_transcricao(texto: str, max_por_categoria: int = 4) -> dict:
    """
    Analisa transcrição de entrevista e retorna pontos_fortes, pontos_fracos e anotacoes.
    Nenhuma dependência externa — usa apenas TF-IDF e dicionário de keywords.
    """
    limpo = _limpar(texto)
    sents = _sentencas(limpo)

    if not sents:
        return {"pontos_fortes": [], "pontos_fracos": [], "anotacoes": ""}

    scores = _pontuar(sents)
    ranking = sorted(zip(scores, sents), key=lambda x: x[0], reverse=True)

    fortes:  list[str] = []
    fracos:  list[str] = []
    neutros: list[str] = []

    for _score, sent in ranking:
        cat = _classificar(sent)
        if cat == "forte" and len(fortes) < max_por_categoria:
            frase = _resumir(sent)
            if frase not in fortes:
                fortes.append(frase)
        elif cat == "fraco" and len(fracos) < max_por_categoria:
            frase = _resumir(sent)
            if frase not in fracos:
                fracos.append(frase)
        elif cat == "neutro" and len(neutros) < 5:
            neutros.append(sent)

    candidatas = neutros[:3] if len(neutros) >= 2 else [s for _, s in ranking[:3]]
    anotacoes = " ".join(candidatas)

    return {
        "pontos_fortes": fortes,
        "pontos_fracos": fracos,
        "anotacoes"    : anotacoes,
    }
