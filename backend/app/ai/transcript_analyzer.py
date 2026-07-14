"""
Sumarização extrativa de transcrições de entrevistas.

Algoritmo:
  1. Limpa artefatos de transcrição (timestamps, labels de falante)
  2. Divide em sentenças (mínimo 30 chars para filtrar fragmentos)
  3. Pontua relevância por TF-IDF
  4. Classifica cada sentença como forte / fraco / neutro por dicionário de keywords
     usando fronteira de palavra para tokens simples — evita "forte" bater em "esforço"
  5. Dentro de cada categoria ordena por TF-IDF; keyword wins, TF-IDF desempata
  6. Anotações: melhor sentença neutra de alta relevância (não um join bruto)
"""
import re
from collections import Counter
from math import log

# ─── Vocabulários de classificação (PT + EN) ──────────────────────────────────

_FORTES_PALAVRAS = {
    "liderança", "liderando", "liderou", "liderei", "gerenciei", "gerenciou",
    "coordenei", "coordenou", "desenvolvi", "desenvolveu", "implementei", "implementou",
    "criei", "criou", "entreguei", "entregou", "alcancei", "alcançou",
    "melhorei", "melhorou", "otimizei", "otimizou", "resolvi", "resolveu",
    "domínio", "dominio", "domina", "sólido", "sólida",
    "avançado", "avançada", "experiente", "excelente", "fluente",
    "certificado", "certificada", "especialista", "proativo", "proativa",
    "autonomia", "iniciativa", "conquista", "reconhecimento",
    "led", "managed", "developed", "implemented", "delivered", "achieved",
    "improved", "optimized", "expert", "fluent", "certified", "proactive", "ownership",
}

_FORTES_FRASES = {
    "trabalho em equipe", "comunicação clara", "mentoria de", "mentorei a equipe",
    "strong leadership", "team work", "cross-functional",
    "nada negativo", "nada a reclamar", "nothing negative",
}

_FRACOS_PALAVRAS = {
    "básico", "básica", "superficial", "iniciante", "introdutório",
    "dificuldade", "dificuldades", "difícil", "desafiador",
    "fraqueza", "fraco", "fraca", "limitado", "limitada",
    "weakness", "struggle", "struggled", "beginner", "limited",
}

_FRACOS_FRASES = {
    "nunca trabalhei", "nunca usei", "nunca aprendi", "não tenho", "não trabalhei", "não sei",
    "não conheço", "não domino", "pouco conhecimento",
    "aprendi recentemente", "estou aprendendo", "estudando ainda",
    "falta de", "faltou", "faltava",
    "preciso melhorar", "quero melhorar", "ainda não",
    "never worked", "lack of", "need to improve",
}

# ─── Pré-processamento ────────────────────────────────────────────────────────

def _limpar(texto: str) -> str:
    # 1. Remove timestamps: [00:05:12], 1:30, (0:00:08)
    texto = re.sub(r'[\[\(]?\d{1,2}:\d{2}(?::\d{2})?[\]\)]?', '', texto)
    # 2. Remove labels com dois-pontos: "Ana (RH):", "João:", "Entrevistador:"
    texto = re.sub(r'^\s*[A-ZÀ-Úa-zà-ú][A-Za-zÀ-ú ]{0,30}(?:\s*\([^)]{1,20}\))?\s*:\s*', '', texto, flags=re.MULTILINE)
    # 3. Remove linhas que são apenas nome de falante sem dois-pontos (Google Meet/Zoom)
    #    ex: "Ana (RH)", "João Silva", "Candidato" — cada palavra começa com maiúscula
    #    Requer que TODOS os tokens comecem com maiúscula para evitar remover conteúdo legítimo
    texto = re.sub(r'^\s*(?:[A-ZÀ-Ú][A-Za-zÀ-ú]*\s*)+(?:\([^)]{1,20}\))?\s*$', '', texto, flags=re.MULTILINE)
    # 4. Remove anotações de ruído: [inaudível], [risos], (pausa)
    texto = re.sub(r'[\[\(][^\[\]\(\)\d]{1,30}[\]\)]', ' ', texto)
    # 5. Remove tags HTML
    texto = re.sub(r'<[^>]+>', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _sentencas(texto: str) -> list[str]:
    partes = re.split(r'(?<=[.!?])\s+|\n{2,}', texto)
    return [s.strip() for s in partes if len(s.strip()) > 30]


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


# ─── Classificação ────────────────────────────────────────────────────────────

def _contar_keywords(palavras: set[str], frases: set[str], txt: str) -> int:
    """
    Conta keywords com verificação de fronteira de palavra para tokens simples,
    e substring para frases compostas. Evita falsos positivos como
    'forte' batendo em 'esforço' ou 'conforto'.
    """
    palavras_txt = set(re.findall(r'\b[a-zA-ZÀ-ú]+\b', txt))
    n  = sum(1 for k in palavras if k in palavras_txt)
    n += sum(1 for f in frases   if f in txt)
    return n


def _classificar(sentenca: str) -> str:
    txt = sentenca.lower()
    pos = _contar_keywords(_FORTES_PALAVRAS, _FORTES_FRASES, txt)
    neg = _contar_keywords(_FRACOS_PALAVRAS, _FRACOS_FRASES, txt)
    if pos > neg:
        return "forte"
    if neg > pos:
        return "fraco"
    return "neutro"


def _resumir(sentenca: str, max_len: int = 130) -> str:
    s = sentenca.strip().rstrip('.,;:!?')
    if len(s) <= max_len:
        return s
    return s[:max_len].rsplit(' ', 1)[0].rstrip('.,;:') + '…'


# ─── API pública ─────────────────────────────────────────────────────────────

def analisar_transcricao(texto: str, max_por_categoria: int = 4) -> dict:
    """
    Analisa transcrição de entrevista e retorna pontos_fortes, pontos_fracos e anotacoes.

    Diferente de ordenar por TF-IDF e depois classificar (o que deixa keywords raras
    dominarem), aqui a classificação por keyword é o sinal primário e o TF-IDF
    desempata dentro de cada categoria.
    """
    limpo = _limpar(texto)
    sents = _sentencas(limpo)

    if not sents:
        return {"pontos_fortes": [], "pontos_fracos": [], "anotacoes": ""}

    scores = _pontuar(sents)

    fortes:  list[tuple[float, str]] = []
    fracos:  list[tuple[float, str]] = []
    neutros: list[tuple[float, str]] = []

    for score, sent in zip(scores, sents):
        cat = _classificar(sent)
        if cat == "forte":
            fortes.append((score, sent))
        elif cat == "fraco":
            fracos.append((score, sent))
        else:
            neutros.append((score, sent))

    # Dentro de cada categoria, as mais relevantes (TF-IDF) primeiro
    fortes.sort(key=lambda x: x[0], reverse=True)
    fracos.sort(key=lambda x: x[0], reverse=True)
    neutros.sort(key=lambda x: x[0], reverse=True)

    fortes_final = list(dict.fromkeys(
        _resumir(s) for _, s in fortes[:max_por_categoria]
    ))
    fracos_final = list(dict.fromkeys(
        _resumir(s) for _, s in fracos[:max_por_categoria]
    ))

    # Anotação: melhor sentença neutra de alta relevância (não um join bruto)
    anotacoes = _resumir(neutros[0][1], max_len=200) if neutros else ""

    return {
        "pontos_fortes": fortes_final,
        "pontos_fracos": fracos_final,
        "anotacoes"    : anotacoes,
    }
