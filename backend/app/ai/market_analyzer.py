import httpx
import numpy as np
from collections import Counter
from app.core.config import settings
from app.ai.resume_parser import get_model, vetorizar_texto


# ── Stopwords para filtrar termos sem valor ────────────────────────────────
STOPWORDS = {
    "de", "da", "do", "em", "para", "com", "que", "uma", "um", "os",
    "as", "se", "no", "na", "por", "mais", "como", "são", "não",
    "anos", "ano", "experiência", "área", "vaga", "cargo", "função",
    "profissional", "empresa", "time", "equipe", "buscamos", "procuramos",
    "desejável", "obrigatório", "necessário", "conhecimento", "habilidade",
    "the", "and", "with", "for", "in", "of", "to", "a", "an",
    "experience", "knowledge", "skills", "ability", "team", "work",
}


# ── Coletor Adzuna ─────────────────────────────────────────────────────────

async def coletar_adzuna(titulo_vaga: str, n_paginas: int = 3) -> list[str]:
    """
    Busca vagas reais na Adzuna e retorna lista de textos de requisitos.
    Adzuna é gratuita: cadastre-se em api.adzuna.com para obter as chaves.
    """
    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
        raise ValueError(
            "Configure ADZUNA_APP_ID e ADZUNA_APP_KEY no .env. "
            "Cadastro gratuito em api.adzuna.com"
        )

    textos = []
    base_url = f"https://api.adzuna.com/v1/api/jobs/{settings.ADZUNA_COUNTRY}/search"

    async with httpx.AsyncClient(timeout=30) as client:
        for pagina in range(1, n_paginas + 1):
            url = f"{base_url}/{pagina}"
            response = await client.get(base_url, params={
                "app_id"      : settings.ADZUNA_APP_ID,
                "app_key"     : settings.ADZUNA_APP_KEY,
                "what"        : titulo_vaga,
                "results_per_page": 50,
                "page"        : pagina,
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


# ── Coletor Kaggle ─────────────────────────────────────────────────────────

def coletar_kaggle(titulo_vaga: str) -> list[str]:
    """
    Lê um dataset local do Kaggle com descrições de vagas.
    Baixe em: kaggle.com/datasets/promptcloud/jobs-on-naukricom
    ou:        kaggle.com/datasets/arshkon/linkedin-job-postings
    Salve o CSV em: backend/data/vagas_mercado.csv
    """
    import pandas as pd
    import os

    caminho = "/app/data/vagas_mercado.csv"

    if not os.path.exists(caminho):
        raise FileNotFoundError(
            f"Dataset não encontrado em {caminho}. "
            "Baixe um dataset de vagas do Kaggle e salve como backend/data/vagas_mercado.csv"
        )

    df = pd.read_csv(caminho)

    # tenta identificar a coluna de descrição automaticamente
    colunas_descricao = ["description", "job_description", "descricao", "requirements"]
    colunas_titulo    = ["title", "job_title", "titulo", "position"]

    col_desc  = next((c for c in colunas_descricao if c in df.columns), None)
    col_titulo = next((c for c in colunas_titulo if c in df.columns), None)

    if not col_desc:
        raise ValueError(
            f"Coluna de descrição não encontrada. Colunas disponíveis: {list(df.columns)}"
        )

    # filtra vagas relacionadas ao cargo buscado
    palavras = titulo_vaga.lower().split()
    if col_titulo:
        mask = df[col_titulo].str.lower().apply(
            lambda t: any(p in str(t) for p in palavras)
        )
        df_filtrado = df[mask]
    else:
        df_filtrado = df

    # limita a 200 vagas para não sobrecarregar
    textos = df_filtrado[col_desc].dropna().head(200).tolist()
    print(f"Kaggle: {len(textos)} vagas encontradas para '{titulo_vaga}'")
    return textos


# ── Extração de termos frequentes ─────────────────────────────────────────

def extrair_termos_frequentes(textos: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """
    Conta os termos mais frequentes em todos os textos coletados.
    Retorna lista de (termo, frequência) ordenada por frequência.
    """
    contador = Counter()

    for texto in textos:
        # tokenização simples — divide por espaços e pontuação
        tokens = (
            texto.lower()
            .replace(",", " ").replace(".", " ").replace(";", " ")
            .replace("(", " ").replace(")", " ").replace("/", " ")
            .split()
        )
        # filtra stopwords e tokens muito curtos
        tokens_validos = [
            t for t in tokens
            if len(t) > 2 and t not in STOPWORDS
        ]
        contador.update(tokens_validos)

    return contador.most_common(top_n)


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