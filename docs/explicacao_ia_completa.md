# Sistema de IA do SIRS v2 — Explicação Completa

> Documento técnico detalhado: como funciona cada módulo de inteligência artificial,
> do momento em que o candidato é criado até a contratação.

---

## Sumário

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Embeddings — Transformar Texto em Números](#2-embeddings--transformar-texto-em-números)
3. [Segmentação do Currículo — `section_extractor.py`](#3-segmentação-do-currículo--section_extractorpy)
4. [Parsing do Currículo — `resume_parser.py`](#4-parsing-do-currículo--resume_parserpy)
5. [Extração de Features Estruturais — `feature_extractor.py`](#5-extração-de-features-estruturais--feature_extractorpy)
6. [Motor de Scoring — `matching_engine.py`](#6-motor-de-scoring--matching_enginepy)
7. [Analisador de Mercado e TF-IDF — `market_analyzer.py`](#7-analisador-de-mercado-e-tf-idf--market_analyzerpy)
8. [Pipeline Celery — `tasks.py`](#8-pipeline-celery--taskspy)
9. [Analisador de Transcrições — `transcript_analyzer.py`](#9-analisador-de-transcrições--transcript_analyzerpy)
10. [Fluxo Completo: Candidato Criado → Contratado](#10-fluxo-completo-candidato-criado--contratado)
11. [Sistema de Auditoria — Campo `historico`](#11-sistema-de-auditoria--campo-historico)

---

## 1. Visão Geral da Arquitetura

O sistema de IA do SIRS v2 tem **dois eixos de avaliação** por candidato:

```
                    ┌─────────────────────────────────────────┐
                    │              CURRÍCULO                  │
                    │  texto → embedding 384-dim (pgvector)   │
                    └──────────────┬──────────────────────────┘
                                   │
               ┌───────────────────┼───────────────────────┐
               ▼                                           ▼
    ┌─────────────────────┐              ┌──────────────────────────┐
    │   score_rh (0–100)  │              │  score_mercado (0–100)   │
    │   CV vs. requisitos │              │  CV vs. vetor de mercado │
    │   da vaga (semântico│              │  (skills do mercado para │
    │   + seção exp)      │              │  aquele cargo)           │
    └──────────┬──────────┘              └───────────┬──────────────┘
               │                                     │
               └────────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  bonus_estrutural        │
                    │  (±0.25 baseado em       │
                    │  anos exp + senioridade  │
                    │  + overlap de skills)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   score_curriculo (0–100)│
                    │   = (rh×peso_rh) +       │
                    │     (mkt×peso_mkt) +     │
                    │     bonus_estrutural      │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┴──────────────────┐
               ▼                                    ▼
    ┌──────────────────┐              ┌──────────────────────────┐
    │ Entrevista RH    │              │  Entrevista Técnica       │
    │ (nota 0–10 +     │              │  (nota 0–10 + transcrição)│
    │  transcrição)    │              └───────────┬──────────────┘
    └──────────┬───────┘                          │
               └────────────────┬─────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   score_total (0–100)    │
                    │   média ponderada de     │
                    │   currículo + entrevistas│
                    └─────────────────────────┘
```

**Stack técnico:**
- **sentence-transformers** — gera embeddings de 384 dimensões (modelo `paraphrase-multilingual-MiniLM-L12-v2` por padrão)
- **pgvector** — armazena e compara vetores diretamente no PostgreSQL 16
- **Celery + Redis** — processa PDFs e análise de mercado em background (sem bloquear a API)
- **FastAPI** — expõe os endpoints; o processamento pesado é sempre delegado ao worker

---

## 2. Embeddings — Transformar Texto em Números

### O que é um embedding (teoria)

Um **embedding** é a forma de um modelo de linguagem "guardar" o significado de um texto como uma lista de números. O modelo usado no SIRS (`paraphrase-multilingual-MiniLM-L12-v2`) foi treinado em centenas de milhões de pares de frases em dezenas de idiomas. Durante o treinamento, ele aprendeu a projetar frases semanticamente parecidas para pontos próximos num espaço de 384 dimensões.

Pense assim: o modelo criou um mapa onde cada texto ocupa uma posição. Textos que falam sobre coisas parecidas ficam próximos nesse mapa. Textos que falam sobre coisas completamente diferentes ficam longe. O "mapa" tem 384 eixos — não é 2D nem 3D como mapas geográficos, mas o princípio de distância e proximidade é o mesmo.

Esses 384 números **não têm rótulo** ("este eixo é tecnologia", "este é senioridade"). Eles emergem do treinamento de forma implícita. O que importa é que o modelo aprendeu a representação certa para que CVs de "engenheiro de software" fiquem próximos de vagas de "desenvolvedor back-end", mesmo sem uma palavra em comum.

### Similaridade de cosseno

Para medir o quanto dois textos são semanticamente parecidos, o sistema usa **similaridade de cosseno**: em vez de calcular a distância em linha reta entre dois pontos, mede o ângulo entre os dois vetores.

Por que ângulo e não distância? Porque a *direção* do vetor carrega o significado, e o *tamanho* (magnitude) carrega apenas o volume de informação. Um CV de uma página e um de cinco páginas sobre o mesmo perfil devem ter similaridade alta, mesmo que o vetor do CV maior seja "mais longo". O cosseno só compara direções, então isso funciona corretamente.

O resultado é sempre entre 0 e 1: 1.0 = textos idênticos em significado, ~0.7 = muito parecidos, ~0.4 = alguma relação, ~0.2 = sem relação relevante.

```python
# matching_engine.py
def _cos(a, b):
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))
```

### Como o vetor é gerado no código

```python
# resume_parser.py
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model

def vetorizar_texto(texto: str) -> list[float]:
    vetor = get_model().encode(
        texto,
        normalize_embeddings=True,   # força norma 1 → cos(a,b) = dot(a,b), sem divisão
        show_progress_bar=False,
    )
    return vetor.tolist()   # lista de 384 floats
```

`normalize_embeddings=True` faz com que todos os vetores tenham norma 1 (comprimento 1). Com isso, o cálculo da similaridade de cosseno se reduz a um simples produto escalar (`dot(a, b)`), que é muito mais rápido. O pgvector armazena esses vetores no PostgreSQL e faz as comparações com o operador `<=>`.

### Por que gerar um vetor por seção também?

Um currículo tem partes muito diferentes: resumo profissional, histórico de empregos, lista de skills, formação. Se o CV inteiro for vetorizado de uma vez, o significado dessas partes se dilui numa média.

A solução é gerar três vetores por currículo:
- `vetor_embedding` — o CV inteiro (contexto geral)
- `vetor_secao_exp` — apenas a seção de experiência profissional
- `vetor_secao_skills` — apenas a seção de habilidades técnicas

Quando o `score_rh` é calculado, a seção de experiência tem peso 60% e o CV completo tem 40%. Quando o `score_mercado` é calculado, a seção de habilidades tem peso 60%. Isso faz as partes mais relevantes do CV pesarem mais do que o restante — formação, objetivos e dados pessoais não atrapalham o resultado.

---

## 3. Segmentação do Currículo — `section_extractor.py`

Antes de vetorizar, o sistema **segmenta o currículo em seções** para ter representações mais focadas:

### Estratégia 1: detecção por cabeçalho

```python
_CABECALHOS = {
    "experiencia": [
        r"experi[eê]ncia\s*profissional",
        r"work\s+experience",
        # ...
    ],
    "habilidades": [
        r"habilidades\s+t[eé]cnicas",
        r"skills",
        r"stack\s+tecnol[oó]gico",
        # ...
    ],
    # ... + educacao, resumo
}
```

Percorre linha por linha. Se uma linha curta (≤60 chars) bate com um padrão, vira "cabeçalho atual" — as linhas seguintes vão para aquela seção.

### Estratégia 2: fallback por densidade semântica

Quando o CV não tem cabeçalhos explícitos (ex: CV em PDF sem formatação), divide em parágrafos e atribui cada parágrafo à seção com mais palavras-chave:

```python
_KEYWORDS_FALLBACK = {
    "habilidades": ["python", "java", "docker", "kubernetes", ...],
    "experiencia": ["responsável", "desenvolvi", "liderou", "empresa", ...],
    "educacao":    ["universidade", "bacharelado", "mestrado", "fatec", ...],
    "resumo":      ["profissional com", "especialista em", "anos de", ...],
}
```

### Por que segmentar?

O vetor da **seção de experiência** é usado com peso 60% no `score_rh`:

```python
# matching_engine.py
def calcular_score_rh_multi_secao(vetor_embedding, vetor_vaga, vetor_secao_exp=None):
    if vetor_secao_exp is not None:
        return 0.60 * cos(vetor_secao_exp, vetor_vaga) + 0.40 * cos(vetor_embedding, vetor_vaga)
    return cos(vetor_embedding, vetor_vaga)
```

A **seção de habilidades** é usada com peso 60% no `score_mercado`. Isso garante que as partes mais relevantes do CV tenham mais peso que o texto completo.

---

## 4. Parsing do Currículo — `resume_parser.py`

Pipeline completo de um arquivo PDF até os vetores:

```python
def parsear_curriculo(caminho_pdf: str) -> dict:
    texto = extrair_texto_pdf(caminho_pdf)    # PyMuPDF (fitz)
    vetor = vetorizar_texto(texto)            # bi-encoder → 384-dim
    secs  = vetorizar_secoes(texto)           # segmenta e vetoriza seções
    return {
        "texto_extraido"    : texto,
        "vetor_embedding"   : vetor,          # vetor do CV completo
        "vetor_secao_exp"   : secs["exp"],    # vetor só da seção de experiência
        "vetor_secao_skills": secs["skills"], # vetor só da seção de habilidades
    }
```

**PDF escaneado (imagem):** se `fitz.open()` não retornar texto, lança `ValueError("PDF não contém texto extraível — pode ser imagem escaneada")`. Nesse caso a candidatura volta para `NOVO` com o erro registrado no histórico.

---

## 5. Extração de Features Estruturais — `feature_extractor.py`

Complementa a análise semântica com **sinais baseados em regras** — sem ML, só regex e dicionários.

### 5.1 Anos de experiência

Estratégia em 3 etapas (prioridade decrescente):

**Etapa 1 — declaração explícita:**
```python
padroes_explicitos = [
    r'(\d{1,2})\s+anos?\s+de\s+experi[eê]ncia',
    r'(\d{1,2})\+?\s*years?\s+of\s+experience',
    r'h[áa]\s+(\d{1,2})\s+anos?\s+trabalh',
    # ...
]
```
Se encontrar "8 anos de experiência" no texto, retorna 8.0.

**Etapa 2 — soma de intervalos de emprego:**
```python
_PAD_INTERVALO = re.compile(
    r'((?:19|20)\d{2})\s*[–\-—]\s*'
    r'(?:((?:19|20)\d{2})|(presente|atual|current))',
    re.IGNORECASE,
)
```
Encontra padrões como "2018–2022" e "2020 - atual", soma as durações **eliminando sobreposições** (se dois empregos se sobrepõem, conta o período uma só vez).

**Etapa 3 — fallback conservador:**
Pega o menor ano encontrado no texto da seção de experiência, calcula `ano_atual - min_ano` e divide por 1.4 (fator de conservadorismo).

### 5.2 Nível de senioridade

```python
_SENIORIDADE = {
    'estagiário': 0, 'trainee': 0,
    'júnior': 1,
    'pleno': 2,
    'sênior': 3, 'especialista': 3,
    'tech lead': 4, 'líder técnico': 4, 'arquiteto': 4,
    'head': 5, 'coordenador': 5, 'gerente': 5,
    'diretor': 6, 'vp': 6, 'cto': 6,
}
```
Busca as expressões mais longas primeiro (evita "lead" bater em "tech lead" antes).

### 5.3 Habilidades técnicas

Catálogo de ~150 skills canônicas (`_HABILIDADES_TECH`) mais um mapa de aliases:

```python
_ALIASES = {
    'k8s': 'kubernetes',
    'postgres': 'postgresql',
    'js': 'javascript',
    'ec2': 'aws', 's3': 'aws', 'lambda': 'aws',  # serviços AWS → 'aws'
    'ingles': 'inglês', 'english': 'inglês',
    # ...
}
```

Para cada skill, procura no texto com **word boundary** para evitar falsos positivos:

```python
_WB  = r'(?<![a-z0-9\+\#\.])'  # word-boundary esquerdo
_WB_R = r'(?![a-z0-9\+\#\.])'  # word-boundary direito

def _encontra_skill(texto_lower, patterns):
    for p in patterns:
        m = re.search(_WB + re.escape(p) + _WB_R, texto_lower)
        if m:
            return m.start()
    return -1
```

### 5.4 Proficiência por skill

Para cada skill detectada, examina uma janela de ±70 chars em volta da menção:

```python
def _extrair_proficiencia(texto, habilidades):
    for skill in habilidades:
        janela = texto[max(0, pos-70) : pos+len(skill)+70]
        if any(m in janela for m in _PROF_BAIXO):  # "básico", "iniciante"
            resultado[skill] = 0.3
        elif any(m in janela for m in _PROF_ALTO):  # "avançado", "expert", "domínio"
            resultado[skill] = 1.3
        else:
            resultado[skill] = 1.0
```

Resultado: "Python avançado" → peso 1.3; "noções de Docker" → peso 0.3.

### 5.5 Bônus estrutural

Combina todos os sinais em um número entre **-0.25 e +0.25** que é somado ao score combinado:

```python
def calcular_bonus_estrutural(features_curriculo, features_vaga) -> float:
    bonus = 0.0

    # 1. Overlap de habilidades (±0.08 máx, proporcional ao coverage)
    skills_comuns = hab_req & hab_cand
    if skills_comuns:
        peso_total = sum(profic.get(s, 1.0) for s in skills_comuns)
        overlap = peso_total / len(hab_req)
        bonus += overlap * 0.08
    else:
        bonus -= 0.15  # tem skills, mas nenhuma bate com a vaga

    # 2. Experiência (escalonada pelo overlap — não penaliza duas vezes)
    escala = max(overlap, 0.3) if hab_req else 1.0
    if ratio >= 1.0:     bonus += 0.08 * escala
    elif ratio >= 0.7:   bonus += 0.03 * escala
    elif ratio < 0.35:   bonus -= 0.10 * escala

    # 3. Senioridade (penalidade proporcional ao gap)
    diff = nivel_cand - nivel_req
    if diff == 0:    bonus += 0.07   # nível exato
    elif diff == 1:  bonus += 0.03   # um acima: levemente ok
    elif diff > 1:   bonus -= 0.01   # muito acima: possível overqualification
    elif diff == -1: bonus -= 0.05   # um abaixo
    elif diff == -2: bonus -= 0.10
    else:            bonus -= 0.15   # 3+ níveis abaixo: mismatch severo

    return max(-0.25, min(0.25, bonus))
```

**Princípio de design:** o bônus estrutural é *pequeno* intencionalmente. Ele complementa o sinal semântico dos embeddings, não substitui. Um currículo semanticamente fraco não é salvo por anos de experiência.

---

## 6. Motor de Scoring — `matching_engine.py`

### 6.1 Score RH (semântico com seção)

```python
def calcular_score_rh_multi_secao(vetor_embedding, vetor_vaga, vetor_secao_exp=None):
    if vetor_secao_exp is not None:
        return 0.60 * cos(vetor_secao_exp, vetor_vaga) + 0.40 * cos(vetor_embedding, vetor_vaga)
    return cos(vetor_embedding, vetor_vaga)
```

Resultado: float entre 0 e 1 (similaridade de cosseno).

### 6.2 Score Mercado

```python
def calcular_score_mercado(vetor_curriculo, vetor_mercado, vetor_secao_skills=None):
    if vetor_secao_skills is not None:
        return 0.60 * cos(vetor_secao_skills, vetor_mercado) + 0.40 * cos(vetor_curriculo, vetor_mercado)
    return cos(vetor_curriculo, vetor_mercado)
```

O `vetor_mercado` é gerado pelo `market_analyzer.py` a partir das skills mais demandadas pelo mercado para aquele cargo.

### 6.3 Score Currículo (combinado)

```python
def calcular_score_curriculo(score_rh, score_mercado, peso_rh, peso_mercado, bonus_estrutural=0.0):
    score = (score_rh * peso_rh) + (score_mercado * peso_mercado) + bonus_estrutural
    return round(max(0.0, min(1.0, score)) * 100, 1)
```

Pesos configurados por vaga (ex: `peso_rh=0.6`, `peso_mercado=0.4`). O bônus é aplicado ao score combinado final.

### 6.4 Score Final (com entrevistas)

```python
def calcular_score_final(score_curriculo, score_entrevista_rh, score_entrevista_tec,
                         peso_curriculo, peso_entrevista_rh, peso_entrevista_tec):
    soma = (score_curriculo / 100) * peso_curriculo
    peso_ativo = peso_curriculo

    if score_entrevista_rh is not None:
        soma       += (score_entrevista_rh / 10) * peso_entrevista_rh
        peso_ativo += peso_entrevista_rh

    if score_entrevista_tec is not None:
        soma       += (score_entrevista_tec / 10) * peso_entrevista_tec
        peso_ativo += peso_entrevista_tec

    return round((soma / peso_ativo) * 100, 1)
```

Notas de entrevista são em escala 0–10; o currículo é 0–100. A fórmula normaliza tudo para 0–1 antes de combinar, e só inclui um peso se a nota existir (candidato pode ir para contratado sem entrevista técnica).

### 6.5 Explicação XAI

```python
def gerar_explicacao(score_rh, score_mercado, score_curriculo, peso_rh, peso_mercado,
                     features_cv=None, features_vaga=None, bonus_estrutural=0.0) -> dict:
    return {
        "score_final": score_curriculo,
        "bonus_estrutural": round(bonus_estrutural * 100, 1),
        "componentes": {
            "aderencia_vaga": {
                "score": round(score_rh * 100, 1),
                "peso": "60%",
                "contribuicao": round(score_rh * peso_rh * 100, 1),
                "classificacao": "bom"  # "excelente" ≥80, "bom" ≥65, "regular" ≥50
            },
            "aderencia_mercado": { ... },
        },
        "sinais_estruturais": {
            "anos_experiencia": 8,
            "nivel_senioridade": 3,
            "habilidades": ["aws", "docker", "fastapi", "postgresql", ...],
            "habilidades_em_comum": ["aws", "postgresql"],  # CV ∩ vaga
            "habilidades_ausentes": ["kubernetes"],         # vaga - CV
        },
        "resumo": "Score 78.5/100 — 45.0 pts da vaga e 28.0 pts do mercado.",
    }
```

Este dict é salvo no banco (`curriculo.explicacao`) e exibido na tela de detalhe do candidato.

---

## 7. Analisador de Mercado e TF-IDF — `market_analyzer.py`

O `market_analyzer` responde à pergunta: **"quais são as skills mais demandadas pelo mercado para este cargo?"**. Ele gera um `vetor_mercado` usado para calcular o `score_mercado` de cada candidato.

A lógica por trás disso é importante: a vaga cadastrada pelo RH pode ser genérica demais ou muito específica, e as palavras que o recrutador usou não necessariamente cobrem todas as skills relevantes. Ao consultar centenas de vagas reais do mercado para o mesmo cargo, o sistema descobre de forma independente o que as empresas *de verdade* estão pedindo — e avalia o candidato também por essa régua.

### 7.1 TF-IDF — o que é e por que funciona aqui (teoria)

**TF** (Term Frequency) mede com que frequência um termo aparece num documento. **IDF** (Inverse Document Frequency) mede o quão *raro* esse termo é em relação ao conjunto de documentos. O produto TF × IDF resulta num score que é alto para termos que aparecem bastante num documento específico, mas que não são comuns em todos os outros documentos.

Traduzindo para o contexto do SIRS: o "corpus" são as vagas coletadas do mercado para um cargo. Se "autocad" aparece em 80% das vagas de Engenheiro Civil, mas quase nunca em vagas de outros cargos, o TF-IDF dele será alto — ele é *característico* daquele cargo. Já "excel" aparece em praticamente tudo (engenharia, finanças, RH, direito), então o IDF dele é baixo — ele não discrimina, não diz nada específico sobre aquele cargo.

Na prática: em vez de retornar "as skills mais *frequentes*" (que seriam as genéricas), o TF-IDF retorna "as skills mais *características*" daquele grupo de vagas. É a diferença entre dizer "engenheiro civil usa excel" (verdade, mas inútil) e "engenheiro civil usa revit, sinapi e nr-18" (discriminativo, útil).

**TF simplificado:** no código, TF é binário (0 ou 1 por documento) — conta se a skill aparece naquele anúncio, não quantas vezes. Para vagas de emprego, uma skill mencionada uma vez já é sinal suficiente.

### 7.2 Detecção de categoria

```python
CATEGORIAS_NORM = {
    "tech":             {"desenvolvedor", "python", "software", "dados", "cloud", ...},
    "direito":          {"advogado", "juridico", "tributario", "oab", ...},
    "rh":               {"recursos humanos", "recrutamento", "people", ...},
    "engenharia_civil": {"engenheiro civil", "obras", "arquiteto", "urbanista", ...},
    "saude":            {"medico", "nutricionista", "enfermeiro", "clinico", ...},
    "financeiro":       {"contador", "controladoria", "auditoria", ...},
    "marketing":        {"marketing", "seo", "social media", "growth", ...},
    "educacao":         {"professor", "docente", "bncc", "pedagogo", ...},
}
```

Normaliza o título (remove acentos, lowercase) e verifica se alguma palavra-chave está contida nele.

### 7.3 Fontes de dados

**Fonte 1 — Kaggle (dataset LinkedIn de vagas americanas):**
- Arquivo local: `/app/data/postings.csv`
- Coluna usada: `skills_desc` (lista de skills separadas por vírgula)
- O título é traduzido para inglês (Google Translate → fallback para dicionário local `_VOCAB_PT_EN`)
- Busca progressiva: título completo → palavras individuais → título em inglês

**Fonte 2 — Adzuna (API de vagas ao vivo):**
- API REST com `ADZUNA_APP_ID` e `ADZUNA_APP_KEY`
- Busca por país configurado em `ADZUNA_COUNTRY`
- Retorna descrições de vagas ao vivo
- Busca progressiva: título completo → palavras individuais → tradução EN

**Configuração `MARKET_ANALYZER_SOURCE`:**
- `"kaggle"` — usa só Kaggle (bom para tech)
- `"adzuna"` — usa só Adzuna (bom para direito, saúde, educação)
- `"ambos"` — usa as duas fontes e combina (Adzuna com peso 2×)

### 7.4 TF-IDF simplificado no código (extração Adzuna)

```python
def extrair_de_adzuna(textos, top_n=30, categoria=None):
    skills_busca = SKILLS_POR_CATEGORIA.get(categoria, SKILLS_GENERICAS)

    # Conta em quantas vagas cada skill aparece (IDF)
    doc_freq = Counter()
    for texto in textos:
        skills_nesse_doc = set()
        for skill in skills_busca:
            if skill in TERMOS_GENERICOS: continue
            if re.search(r'\b' + re.escape(skill) + r'\b', texto.lower()):
                skills_nesse_doc.add(skill)
        for skill in skills_nesse_doc:
            doc_freq[skill] += 1

    # TF-IDF simplificado
    scores = Counter()
    for skills in skill_por_doc:
        for skill in skills:
            tf  = 1                                        # presença binária
            idf = math.log(n_docs / (1 + doc_freq[skill]))
            scores[skill] += tf * idf
```

**O que significa IDF aqui:**
- Uma skill que aparece em **todas** as vagas tem IDF próximo de zero (é genérica — ex: "excel")
- Uma skill que aparece em **poucas** vagas tem IDF alto (é específica — ex: "revit" para obras)
- O resultado final ordena as skills pelo quanto são **características** daquele conjunto de vagas, não pelo quanto são **frequentes**

**Prevenção de contaminação cruzada:** o parâmetro `categoria` limita quais skills são buscadas. A categoria `"saude"` só busca `{"crm", "coren", "anvisa", "bls", "dietoterapia", ...}` — nunca vai encontrar "hidráulica" (que está só em `"engenharia_civil"`).

### 7.5 Stopwords e filtros de ruído

Sem filtragem, os dados brutos do mercado produzem muito lixo. O sistema tem três camadas de limpeza:

---

**Camada 1 — `TERMOS_GENERICOS` (sempre bloqueados, qualquer categoria):**

São termos que parecem skills mas na verdade são benefícios, requisitos legais ou palavras tão genéricas que não dizem nada sobre o perfil do candidato. Nenhum deles passa para o vetor de mercado, independente do cargo:

```python
TERMOS_GENERICOS = {
    "clt", "benefícios", "vale transporte", "vale refeição",
    "plano de saúde", "fgts", "inss", "férias", "13º",
    "carteira assinada", "pj", "mei", "holerite", "rescisão",
    # "sem" em PT significa "without" — colide com SEM (Search Engine Marketing)
    "sem",
    # escolaridade mínima — não é skill
    "ensino médio", "ensino fundamental", "educação infantil",
    # cota legal — não é skill
    "pcd",
}
```

---

**Camada 2 — `limpar_skills_desc` (específico para dados Kaggle/LinkedIn):**

O campo `skills_desc` do LinkedIn pode vir como lista limpa ("Python,Docker,AWS") ou como texto corrido cheio de artefatos. Esta função filtra cada item antes de contá-lo:

```python
def limpar_skills_desc(texto):
    # Trunca antes de boilerplate EEO ("equal opportunity employer", etc.)
    # — evita que "color", "religion", "age" virem skills
    for marker in _EEO_MARKERS:
        idx = texto_lower.find(marker)
        if idx != -1:
            texto = texto[:comma_before]  # corta antes da vírgula anterior

    for parte in partes:
        if len(parte) > 45:        continue  # texto corrido, não skill
        if len(parte) < 2:         continue  # muito curto
        if primeira_palavra in _PRIMEIRA_PALAVRA_FRASE:
            continue  # começa com "we", "our", "the", "must", "ability", ...
        if len(parte.split()) > 5: continue  # frase, não skill

        # Filtros de artefatos de sistema:
        if re.search(r'^pi[0-9a-f]{6,}', parte.lower()):  continue  # hash IDs internos
        if re.search(r'\d{5,}', parte):                    continue  # sequência longa de dígitos
        if re.search(r'\d+\s*year', parte.lower()):        continue  # "2 years", "5 year"
        if re.search(r'\([a-z/]{2,}\)', parte.lower()):    continue  # "(mar/com)", "(uxd)"
        if ' / ' in parte and len(parte) > 15:             continue  # "social media / blogging"
        if re.search(r'college|university|degree', parte.lower()): continue  # escolaridade
        if '=' in parte:                                   continue  # "jobprofile=production manager"
        if '$' in parte or re.search(r'^\d{3,}', parte):  continue  # fragmentos de salário
        if '/' in parte and ' / ' not in parte and len(parte) > 12: continue  # "certification/education"
```

A maioria desses filtros foi adicionada após testes reais revelarem ruído específico no dataset do Kaggle: IDs de sistema com hash, requisitos de anos de experiência formatados como skills, categorias internas do LinkedIn com abreviações em parênteses, fragmentos de descrição de salário.

---

**Camada 3 — `stopwords` em `extrair_de_kaggle` (lista extensa):**

Mesmo após `limpar_skills_desc`, alguns termos passam e precisam ser bloqueados explicitamente. A lista cobre quatro grupos de problemas reais encontrados durante os testes:

```python
stopwords = {
    # Termos genéricos de RH sem valor técnico
    "management", "solutions", "experience", "skills", "knowledge",
    "strong", "work", "working", "role", "team", "business",
    "communication", "verbal", "written",

    # ONG / setor público — contaminam buscas genéricas
    "community outreach", "disaster response", "fundraising",
    "nonprofit", "non-profit", "ngo", "grant writing", "advocacy",

    # Ruído interno do Kaggle (categorias do LinkedIn)
    "resources", "pajobs", "automation", "engineer", "lead", "data",

    # Soft skills sem valor diferenciador
    "organization", "problem solving", "good attitude",
    "time management", "teamwork", "adaptability",
    "multitasking", "interpersonal skills", "critical thinking",

    # Requisitos físicos ADA (Americans with Disabilities Act)
    # — aparecem em vagas operacionais americanas
    "kneel", "bend", "lift", "stand", "sit", "walk", "climb",
    "stoop", "crouch", "handle or feel objects", "reach with hands",
    "color vision", "peripheral vision", "depth perception",
    "close vision", "distance vision",

    # Vagas de escolas religiosas americanas
    "apologetics", "biblical worldview integration", "ministry",
    "theological", "seminary",

    # EEO blacklist — classes protegidas que passam pelo split
    "race", "color", "religion", "gender", "disability", "age",
    "veteran", "equal opportunity", "affirmative action",
    # ... + benefícios: "dental", "vision", "401k", "pto", ...
} | _EEO_BLACKLIST
```

O grupo de requisitos físicos ADA merece destaque: vagas de chão de fábrica americanas listam literalmente "ability to kneel, bend, lift 50 lbs" como skills no campo `skills_desc`. Sem esse filtro, "kneel" e "bend" apareceriam no ranking de skills de cargos como "Analista de Dados" — porque algumas vagas de analista estão no mesmo dataset que vagas operacionais.

---

### 7.6 Geração do vetor de mercado

```python
def gerar_vetor_mercado(termos_frequentes):
    termos = [t[0] for t in termos_frequentes]
    pesos  = np.array([t[1] for t in termos_frequentes], dtype=float)
    pesos /= pesos.sum()  # normaliza para somar 1

    # Traduz para português (os currículos BR estão em PT)
    termos_pt = [traduzir_para_portugues(t) for t in termos]

    # Vetoriza cada skill individualmente
    vecs = model.encode(termos_pt, normalize_embeddings=True)

    # Média ponderada pelos scores TF-IDF
    vetor_mercado = np.average(vecs, axis=0, weights=pesos)
    vetor_mercado = vetor_mercado / np.linalg.norm(vetor_mercado)  # re-normaliza

    return vetor_mercado.tolist()
```

O resultado é um vetor de 384 dimensões que representa o "perfil técnico médio exigido pelo mercado" para aquele cargo. Quanto mais próximo o CV estiver deste vetor, maior o `score_mercado`.

### 7.7 Fallback para skills curadas

Se o mercado retornar menos de 10 vagas (API offline, cargo muito específico), o sistema usa uma lista curada manualmente:

```python
SKILLS_CURADAS = {
    "tech":            [("python", 100), ("aws", 90), ("docker", 85), ...],
    "direito":         [("oab", 100), ("direito tributário", 90), ...],
    "engenharia_civil":[("autocad", 100), ("revit", 90), ("bim", 85), ...],
    # ... 9 categorias no total
}
```

---

## 8. Pipeline Celery — `tasks.py`

Há duas tasks principais:

### 8.1 `processar_curriculo` (PDF)

```
PDF enviado
    │
    ▼
parsear_curriculo(caminho_pdf)
    ├── extrair_texto_pdf()      ← PyMuPDF
    ├── vetorizar_texto()        ← bi-encoder → vetor 384-dim do CV completo
    └── vetorizar_secoes()       ← section_extractor → vetores exp + skills

extrair_features_curriculo(texto_extraido)
    ├── _extrair_anos_curriculo()
    ├── _extrair_nivel()
    ├── _extrair_habilidades()
    └── _extrair_proficiencia()

extrair_features_vaga(vaga.requisitos_texto, termos_mercado)
    ├── anos mínimos
    ├── nível esperado
    └── habilidades do texto da vaga

calcular_bonus_estrutural(feat_cv, feat_vaga)

calcular_score_rh_multi_secao(vetor_cv, vetor_vaga, vetor_exp)
calcular_score_mercado(vetor_cv, vetor_mercado, vetor_skills)
calcular_score_curriculo(score_rh, score_mercado, peso_rh, peso_mkt, bonus)

gerar_explicacao(...)

_verificar_nome_cv()     ← nome cadastrado aparece nos 1os 300 chars do CV?

Salva no banco:
    curriculo.texto_extraido, vetor_embedding, vetor_secao_exp, vetor_secao_skills
    curriculo.score_rh, score_mercado, score_curriculo, explicacao
    candidatura.score_total
    candidatura.status: PROCESSANDO → TRIAGEM_PENDENTE

_notificar_rh()          ← email para o RH responsável pela vaga
```

### 8.2 `atualizar_mercado_vaga`

```
Vaga criada / POST /vagas/{id}/analisar-mercado
    │
    ▼
analisar_mercado(vaga.nome)
    ├── detectar_categoria()
    ├── coletar_adzuna()     ← API Adzuna, até 200 descrições
    ├── coletar_kaggle()     ← CSV local, até 300 skills_desc
    ├── extrair_de_adzuna() / extrair_de_kaggle()   ← TF-IDF
    └── gerar_vetor_mercado()

Salva na vaga:
    vaga.vetor_mercado
    vaga.ranking_mercado = {termos, total_vagas, fonte, atualizado_em}

_recalcular_scores_mercado()
    └── Recalcula score_mercado e score_curriculo de TODOS os CVs
        já processados desta vaga com o novo vetor
```

**Retry automático:** todas as tasks têm `max_retries=3`. Erros `ValueError` (irrecuperáveis, ex: PDF sem texto) não retentam — registram o erro no histórico e devolvem a candidatura para `NOVO`.

---

## 9. Analisador de Transcrições — `transcript_analyzer.py`

Analisa o texto da transcrição de uma entrevista e extrai pontos fortes, fracos e anotações.

### Pipeline:

```
Texto da transcrição
    │
    ├── _limpar()
    │     ├── Remove timestamps: [00:05:12], 1:30
    │     ├── Remove labels de falante: "Ana (RH):", "João:"
    │     ├── Remove ruído: [inaudível], [risos]
    │     └── Remove tags HTML
    │
    ├── _sentencas()      ← divide em sentenças (min 30 chars)
    │
    ├── _pontuar()        ← TF-IDF por sentença
    │     └── score = Σ (tf × log((N+1)/(df+1)))  para tokens > 3 chars
    │
    └── Para cada sentença:
          _classificar()
              ├── conta keywords de _FORTES_PALAVRAS / _FORTES_FRASES
              │   ("liderança", "implementei", "fluente", "certificado", ...)
              ├── conta keywords de _FRACOS_PALAVRAS / _FRACOS_FRASES
              │   ("básico", "nunca trabalhei", "dificuldade", ...)
              └── retorna "forte" | "fraco" | "neutro"
```

**Saída:**
```python
{
    "pontos_fortes": ["Liderei equipe de 8 pessoas na migração para cloud", ...],
    "pontos_fracos": ["Nunca trabalhei com Kubernetes", ...],
    "anotacoes":     "Demonstrou boa comunicação e organização clara de ideias"
}
```

**Princípio de design:** a classificação por keyword é o sinal primário; o TF-IDF desempata dentro de cada categoria. Isso evita que sentenças raras mas sem sinal positivo dominem sobre sentenças com palavras-chave claras de competência.

---

## 10. Fluxo Completo: Candidato Criado → Contratado

```
1. RH cria candidato (nome, email, telefone, endereço)

2. RH cria ou seleciona uma vaga
   └── Task Celery: atualizar_mercado_vaga()
       └── Busca skills no mercado → gera vetor_mercado

3. RH submete CV (PDF ou texto)
   └── Candidatura criada: status = NOVO
   └── Task Celery: processar_curriculo()
       ├── status: NOVO → AGUARDANDO_PROC → PROCESSANDO
       ├── Parseia PDF, vetoriza, calcula scores
       ├── status: PROCESSANDO → TRIAGEM_PENDENTE
       └── Envia e-mail ao RH responsável

4. Triagem pelo RH (lê scores, explicação XAI, habilidades em comum)
   ├── Aprovado  → status: TRIAGEM_PENDENTE → APROVADO_TRIAGEM
   ├── Reprovado → status: TRIAGEM_PENDENTE → REPROVADO_TRIAGEM
   └── Guardar   → status: TRIAGEM_PENDENTE → BANCO_TALENTOS

5. Entrevista RH
   ├── Agendamento → status: APROVADO_TRIAGEM → ENTREVISTA_RH_AGENDADA
   └── Realização  → status: ENTREVISTA_RH_AGENDADA → ENTREVISTA_RH_REALIZADA
       ├── RH cola transcrição → transcript_analyzer.analisar_transcricao()
       ├── RH registra nota (0–10)
       └── score_total recalculado

6. Decisão pós-RH
   ├── Passa → status: ENTREVISTA_RH_REALIZADA → ENTREVISTA_TEC_AGENDADA
   └── Reprova → status: ENTREVISTA_RH_REALIZADA → REPROVADO_RH

7. Entrevista Técnica
   └── status: ENTREVISTA_TEC_AGENDADA → ENTREVISTA_TEC_REALIZADA
       ├── Gestor cola transcrição + nota
       └── score_total recalculado (agora inclui entrevista técnica)

8. Decisão Final
   ├── status: ENTREVISTA_TEC_REALIZADA → DECISAO_PENDENTE
   ├── Contratar  → status: DECISAO_PENDENTE → CONTRATADO
   ├── Reprovar   → status: DECISAO_PENDENTE → NAO_APROVADO
   └── Guardar    → status: DECISAO_PENDENTE → BANCO_TALENTOS
```

**score_total em cada estágio:**

| Estágio | Fórmula |
|---|---|
| Após CV | `score_curriculo × peso_curriculo` / `peso_curriculo` |
| Após Entrevista RH | `(score_cv × p_cv + nota_rh × p_rh)` / `(p_cv + p_rh)` |
| Após Entrevista Técnica | `(score_cv × p_cv + nota_rh × p_rh + nota_tec × p_tec)` / `(p_cv + p_rh + p_tec)` |

Pesos padrão configuráveis por vaga: `peso_curriculo=0.5`, `peso_entrevista_rh=0.25`, `peso_entrevista_tec=0.25`.

---

## 11. Sistema de Auditoria — Campo `historico`

Toda candidatura tem um campo `historico` do tipo `JSONB` no PostgreSQL. É uma lista append-only de eventos — nunca se apaga, nunca se modifica.

### Estrutura de uma entrada no histórico

```python
{
    "de"  : "triagem_pendente",
    "para": "aprovado_triagem",
    "ator": "ana.oliveira@empresa.com",  # e-mail do usuário ou "sistema"
    "em"  : "2024-10-18T14:32:11.843Z",  # UTC ISO-8601
}
```

### Tipos de evento registrados

**1. Transições de status** (toda mudança de estado):
```python
def _transicionar(candidatura, novo_status, ator="sistema"):
    historico = list(candidatura.historico or [])
    historico.append({
        "de"  : candidatura.status.value,
        "para": novo_status.value,
        "ator": ator,
        "em"  : datetime.utcnow().isoformat(),
    })
    candidatura.historico = historico
    candidatura.status    = novo_status
```

**2. Alertas do sistema** (sem mudança de status):
```python
# Quando o nome cadastrado não aparece no início do CV
{
    "de"     : "processando_curriculo",
    "para"   : "processando_curriculo",
    "ator"   : "sistema",
    "em"     : "...",
    "alerta" : "nome_cv_divergente",
    "detalhe": "Nome cadastrado 'Lucas Andrade' não foi encontrado no início do CV.
                Tokens ausentes: ['andrade']. Verifique se o CV pertence a este candidato."
}
```

**3. Erros de processamento** (com rollback para NOVO):
```python
{
    "de"  : "processando_curriculo",
    "para": "novo",
    "ator": "sistema",
    "em"  : "...",
    "erro": "PDF não contém texto extraível — pode ser imagem escaneada"
}
```

### Verificação de nome no CV

É uma camada de proteção contra **fraude**: verifica se os tokens do nome cadastrado aparecem nos primeiros 300 chars do CV (onde o nome quase sempre está):

```python
def _verificar_nome_cv(nome_candidato, texto_cv):
    trecho = texto_cv[:300]
    trecho_norm = _normalizar_nome(trecho)  # remove acentos, lowercase

    # Ignora partículas: "de", "da", "do", "e", etc.
    tokens = [t for t in nome_candidato.split()
              if t not in _PARTICULAS and len(t) > 2]

    encontrados = [t for t in tokens if t in trecho_norm]
    confianca   = len(encontrados) / len(tokens)

    return {
        "match"    : confianca >= 0.5,   # não bloqueia, apenas alerta
        "confianca": confianca,
        "tokens_ausentes": [t for t in tokens if t not in trecho_norm],
    }
```

**Importante:** o alerta é **soft** — não bloqueia o processamento nem muda o status. Fica registrado no histórico para que o RH possa verificar manualmente se quiser.

### Transições permitidas (máquina de estados)

```python
TRANSICOES = {
    NOVO:                     [AGUARDANDO_PROC],
    AGUARDANDO_PROC:          [PROCESSANDO],
    PROCESSANDO:              [TRIAGEM_PENDENTE],
    TRIAGEM_PENDENTE:         [APROVADO_TRIAGEM, REPROVADO_TRIAGEM, BANCO_TALENTOS],
    APROVADO_TRIAGEM:         [ENTREVISTA_RH_AGENDADA],
    ENTREVISTA_RH_AGENDADA:   [ENTREVISTA_RH_REALIZADA],
    ENTREVISTA_RH_REALIZADA:  [ENTREVISTA_TEC_AGENDADA, REPROVADO_RH],
    ENTREVISTA_TEC_AGENDADA:  [ENTREVISTA_TEC_REALIZADA],
    ENTREVISTA_TEC_REALIZADA: [DECISAO_PENDENTE, REPROVADO_TECNICO],
    DECISAO_PENDENTE:         [CONTRATADO, NAO_APROVADO, BANCO_TALENTOS],
    REPROVADO_TRIAGEM:        [BANCO_TALENTOS],
    REPROVADO_RH:             [BANCO_TALENTOS],
    REPROVADO_TECNICO:        [BANCO_TALENTOS],
}
```

Qualquer tentativa de transição fora desta tabela lança `ValueError` e é registrada no histórico — nunca altera silenciosamente o estado.

---

*Documento gerado em outubro de 2026 a partir do código-fonte de `backend/app/ai/`.*
*Arquivos lidos diretamente: `resume_parser.py`, `section_extractor.py`, `feature_extractor.py`, `matching_engine.py`, `market_analyzer.py`, `tasks.py`, `transcript_analyzer.py`, `models/candidatura.py`, `api/endpoints/candidaturas.py`.*
