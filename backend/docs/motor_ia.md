# Motor de IA — Documentação Técnica

Como o sistema avalia, ordena e explica candidaturas.

---

## Visão geral do pipeline

Um currículo passa por três estágios de avaliação, em ordem de custo computacional:

```
Upload PDF / texto webhook
        │
        ▼
1. RESUME PARSER ─── extrai texto, gera vetor principal + vetores de seção
        │
        ▼
2. SCORING (Celery task)
   ├─ section_extractor  ── segmenta CV em seções (exp, skills, educação)
   ├─ feature_extractor  ── extrai anos, nível, skills (regex puro)
   ├─ matching_engine    ── score_rh (multi-seção + bônus estrutural)
   └─ market_analyzer    ── score_mercado (já pré-computado na vaga)
        │
        ▼
3. RERANKER (sob demanda, via botão)
   └─ cross-encoder sobre (vaga, trecho_cv) → score_rerank
```

---

## 1. Resume Parser (`resume_parser.py`)

**O que faz:** transforma um arquivo PDF ou texto puro num conjunto de vetores que representam o currículo no espaço semântico.

### Modelo de embedding

Padrão: `all-MiniLM-L6-v2` (configurável via `EMBEDDING_MODEL` no `.env`).

- Produz vetores normalizados de **384 dimensões** (configurável via `EMBEDDING_DIM`).
- Os vetores são normalizados (`normalize_embeddings=True`), então o produto escalar entre dois vetores é igual ao cosseno do ângulo entre eles — valores de −1 a 1, onde 1 = idênticos.
- Carregado em memória via singleton: o modelo é inicializado na primeira chamada e reutilizado em todas as seguintes.

### Funções públicas

| Função | Entrada | Saída |
|---|---|---|
| `vetorizar_texto(texto)` | string qualquer | `list[float]` com 384 dims |
| `vetorizar_secoes(texto)` | texto do currículo | `{"exp": list[float] | None, "skills": list[float] | None}` |
| `parsear_curriculo(caminho_pdf)` | caminho do PDF | `{"texto_extraido", "vetor_embedding", "vetor_secao_exp", "vetor_secao_skills"}` |

### Extração de PDF

Usa **PyMuPDF (fitz)**. Abre o PDF página a página, extrai texto com `get_text("text")`, concatena. Se o PDF for imagem escaneada (sem texto extraível), lança `ValueError`.

### Vetores de seção

Após extrair o texto, `vetorizar_secoes` chama o `section_extractor` para detectar as seções do CV (experiência e habilidades) e vetoriza cada uma separadamente. Se uma seção não for detectada, retorna `None` para ela.

---

## 2. Section Extractor (`section_extractor.py`)

**O que faz:** divide o texto do currículo em seções temáticas para que cada parte seja comparada com a parte correspondente da vaga, em vez de tudo ser diluído num único vetor.

> **Onde é usado — dois contextos distintos:**
>
> 1. **Durante o processamento do currículo (Celery task):** `resume_parser.vetorizar_secoes()` chama `extrair_secoes()` para segmentar o texto e vetoriza a seção de experiência (`vetor_secao_exp`) e a de habilidades (`vetor_secao_skills`). Esses dois vetores são salvos nas colunas `curriculos.vetor_secao_exp` e `curriculos.vetor_secao_skills` e usados permanentemente no cálculo do `score_rh`.
>
> 2. **No reranker (sob demanda):** a função auxiliar `texto_para_rerank()` extrai os ≤ 800 chars mais relevantes do CV (resumo → experiência → habilidades) para servir como entrada ao cross-encoder, que tem limite de tokens.

### Seções detectadas

| Seção | O que captura |
|---|---|
| `experiencia` | Histórico de empregos, responsabilidades, projetos |
| `habilidades` | Stack técnica, ferramentas, competências |
| `educacao` | Formação acadêmica, cursos, certificações |
| `resumo` | Perfil profissional, objetivo, "sobre mim" |

### Estratégia de detecção (duas etapas)

**Etapa 1 — detecção por cabeçalho:**
Percorre o texto linha a linha buscando cabeçalhos curtos (≤ 60 chars) que batam com padrões regex conhecidos, em PT e EN:

```
"EXPERIÊNCIA PROFISSIONAL" → secao = "experiencia"
"HABILIDADES TÉCNICAS"     → secao = "habilidades"
"FORMAÇÃO ACADÊMICA"       → secao = "educacao"
"RESUMO PROFISSIONAL"      → secao = "resumo"
```

Uma linha é considerada cabeçalho se:
- For toda em maiúsculas, OU
- Terminar com ":", OU
- Tiver ≤ 5 palavras E bater com um padrão conhecido

**Etapa 2 — fallback por densidade (para CVs sem cabeçalhos):**
Se uma ou mais seções ficaram vazias, o texto é dividido em parágrafos (separados por `\n\n`). Cada parágrafo recebe a seção cuja lista de palavras-chave características aparece com mais frequência nele:

```
Palavras-chave de "experiencia": "responsável", "trabalhei", "empresa", "cargo"...
Palavras-chave de "habilidades": "python", "docker", "aws", "react"...
```

### Função auxiliar: `texto_para_rerank`

Extrai os ≤ 800 chars mais relevantes do CV na ordem: resumo → experiência → habilidades. Usada pelo cross-encoder para respeitar o limite de tokens do modelo.

---

## 3. Feature Extractor (`feature_extractor.py`)

**O que faz:** extrai sinais estruturados do texto por regex e dicionários, sem nenhum modelo de ML. Esses sinais complementam a similaridade semântica com informações que embeddings ignoram.

### Features extraídas do currículo

#### Anos de experiência

Três estratégias em cascata:

**1. Declaração explícita** (mais confiável):
```
"10 anos de experiência em Python"  → 10.0
"Experiência de 7 anos na área"     → 7.0
"8 anos de mercado financeiro"      → 8.0
```

**2. Soma de intervalos de emprego** detectados no texto:
```
"Empresa A: 2015-2019" + "Empresa B: 2019-2023" → 8 anos
"desde 2018"                                      → ano_atual - 2018
```
Intervalos sobrepostos são mergeados antes de somar (ex: 2015-2019 e 2017-2022 → 2015-2022 = 7 anos, não 9).

**3. Fallback conservador**: se nenhum padrão foi encontrado mas há pelo menos dois anos no texto, usa `(ano_atual - menor_ano) / 1.4` — dividido por 1.4 para compensar que datas de formação inflacionam o span.

#### Nível de senioridade

Dicionário com mapeamento texto → número:
```
estágio/trainee  → 0
júnior           → 1
pleno            → 2
sênior/especialista → 3
tech lead/staff  → 4
head/coordenador/gerente → 5
diretor/VP/CTO   → 6
```
Quando múltiplos níveis aparecem no texto ("avançou de júnior para sênior"), usa o maior.

#### Habilidades técnicas

Catálogo fixo de ~80 skills (`_HABILIDADES_TECH`): linguagens, frameworks, bancos de dados, cloud, DevOps. Usa regex com word-boundary adaptado para termos com pontos (`node.js`) e símbolos (`c++`).

#### Nível de educação

```
0 = sem informação
1 = técnico/tecnólogo
2 = graduação/bacharelado
3 = pós-graduação/MBA
4 = mestrado
5 = doutorado
```
Prioriza a `formacao` (JSONB estruturado da candidatura) sobre extração de texto.

### Bônus estrutural (saída principal)

`calcular_bonus_estrutural(feat_curriculo, feat_vaga) → float ∈ [-0.15, +0.15]`

Três componentes somados:

| Componente | Máximo | Lógica |
|---|---|---|
| Anos de experiência | ±0.06 | candidato cumpre/ultrapassa requisito → +0.06; muito aquém → -0.06 |
| Nível de senioridade | ±0.05 | nível exato → +0.05; um acima → +0.02; dois abaixo → -0.05 |
| Overlap de habilidades | +0.04 | `len(hab_req ∩ hab_cand) / len(hab_req) × 0.04` |

O intervalo ±15% foi escolhido para que o bônus seja um refinamento da similaridade semântica, nunca o determinante.

---

## 4. Market Analyzer (`market_analyzer.py`)

**O que faz:** quando uma vaga é criada, busca dados reais de mercado para identificar as skills mais demandadas para aquele cargo, gera um vetor representando o "perfil médio de mercado" e o usa como segundo eixo de avaliação dos currículos.

### Pipeline

```
título da vaga
      │
      ▼
1. detectar_categoria(título)
   "Dev Python Sênior" → "tech"
   "Advogado Trabalhista" → "direito"
   ...
      │
      ▼
2. Coleta de dados (conforme categoria e MARKET_ANALYZER_SOURCE no .env)
   ├─ coletar_kaggle() → dataset LinkedIn Jobs (~120k vagas, skills_desc CSV)
   └─ coletar_adzuna() → API Adzuna (vagas reais em PT-BR, até 40 resultados)
      │
      ▼
3. Extração de termos frequentes
   ├─ extrair_de_kaggle()  → contagem direta de skills (formato lista CSV)
   └─ extrair_de_adzuna()  → TF-IDF simplificado sobre descrições longas
      │
      ▼
4. Fallback curado se < 10 vagas encontradas
   Skills curadas por categoria (ex: python, aws, docker para "tech")
      │
      ▼
5. gerar_vetor_mercado(termos_frequentes)
   → média ponderada dos vetores de cada termo (peso = frequência)
   → normalizado para unit vector
   → salvo como vaga.vetor_mercado
```

### Extratores de skills

**Kaggle (`extrair_de_kaggle`):**
O dataset LinkedIn tem a coluna `skills_desc` no formato `"Python,Docker,AWS,React"`. O extrator divide por vírgula, filtra frases longas (> 50 chars, que são texto corrido, não skill), remove stopwords e conta a frequência de cada skill.

**Adzuna (`extrair_de_adzuna`):**
As vagas da Adzuna têm descrições livres em texto. Aplica TF-IDF simplificado:
- **TF = 1** (presença binária por documento)
- **IDF = log(N / (1 + df))** onde df = em quantas vagas a skill aparece
- IDF alto = skill específica daquele cargo (valiosa)
- IDF baixo = skill genérica que aparece em tudo (descartada)

Usa um dicionário de ~100 skills por domínio como vocabulário restrito.

### Busca no Kaggle

Traduz o título da vaga para inglês (via `deep-translator`), extrai as palavras com ≥ 4 chars, busca progressivamente cada palavra no campo `title` do dataset. Usa o subconjunto com mais resultados. Se ainda < 30 vagas, busca também no campo `skills_desc`.

### Vetor de mercado

Os top-30 termos extraídos são:
1. Traduzidos de volta para português (para compatibilidade com currículos BR)
2. Vetorizados com o mesmo modelo de embedding
3. Combinados numa média ponderada (peso = frequência normalizada)
4. Normalizados para unit vector

Resultado: um único vetor de 384 dims que representa "o que o mercado espera para este cargo".

---

## 5. Matching Engine (`matching_engine.py`)

**O que faz:** calcula o score final de aderência do currículo à vaga combinando os vetores de seção, o bônus estrutural e o vetor de mercado.

### Score RH (aderência à vaga)

Calculado por `calcular_score_rh_multi_secao` quando há vetores de seção, ou por `calcular_score_rh` (fallback) quando não há.

**Com seção de experiência detectada:**

```
score_rh = 0.60 × sim(vetor_exp_section, vetor_vaga)   # compatibilidade direta
          + 0.40 × sim(vetor_cv_completo, vetor_vaga)   # holística
          + bonus_estrutural × 0.6                      # anos, senioridade, overlap (reduzido)
```

**Sem seções (fallback):**

```
score_rh = sim(vetor_cv_completo, vetor_vaga) + bonus_estrutural_total
```

O bônus estrutural é aplicado com peso total (±0.15).

### Por que a fórmula multi-seção?

O CV de um sênior de 10 anos tem muito texto — objetivos, hobbies, descrições de projetos. Comparar o CV inteiro com a vaga dilui o sinal técnico com ruído. Dar peso maior (60%) à seção de experiência foca a comparação no que realmente importa.

A comparação com o vetor de mercado pertence exclusivamente ao `score_mercado`. Isso garante que um analista que configure `peso_mercado = 0` desative completamente a influência do mercado — ela não fica escondida dentro do `score_rh`.

### Score de mercado

```
# Com seção de habilidades detectada:
score_mercado = 0.60 × sim(vetor_skills_section, vetor_mercado)   # alinhamento técnico focado
              + 0.40 × sim(vetor_cv_completo,    vetor_mercado)   # contexto holístico

# Sem seção (fallback):
score_mercado = sim(vetor_cv_completo, vetor_mercado)
```

Mede o quanto o perfil do candidato se alinha às skills que o mercado está demandando para aquele cargo, independente dos requisitos específicos da vaga. Quando a seção de habilidades foi detectada, a comparação usa esse vetor focado em vez do CV completo — mais sinal, menos ruído.

### Score curricular

```
score_curriculo = (score_rh × peso_rh) + (score_mercado × peso_mercado)
                 × 100  →  escala 0–100
```

Pesos padrão: `peso_rh = 0.6`, `peso_mercado = 0.4`. Configuráveis por vaga.

### Score final consolidado

Calculado depois das entrevistas:

```
score_total = (score_curriculo/100 × peso_curriculo)
            + (score_entrevista_rh/10  × peso_entrevista_rh)
            + (score_entrevista_tec/10 × peso_entrevista_tec)
            × 100
```

Pesos padrão: currículo 50%, entrevista RH 25%, entrevista técnica 25%.

### Explicação XAI

`gerar_explicacao()` produz um dicionário que vai para `candidatura.historico` no evento `curriculo_processado`:

```json
{
  "score_final": 67.5,
  "componentes": {
    "aderencia_vaga":    {"score": 74.2, "peso": "60%", "contribuicao": 44.5, "classificacao": "bom"},
    "aderencia_mercado": {"score": 58.3, "peso": "40%", "classificacao": "regular"}
  },
  "sinais_estruturais": {
    "anos_experiencia": 5.0,
    "nivel_senioridade": 2,
    "habilidades": ["docker", "fastapi", "postgresql", "python"],
    "nivel_educacao": 2,
    "habilidades_em_comum": ["docker", "python"]
  },
  "resumo": "Score 67.5/100 — 44.5 pts da vaga e 23.3 pts do mercado."
}
```

---

## 6. Reranker (`reranker.py`)

**O que faz:** reordena os top-N candidatos de uma vaga com mais precisão do que o bi-encoder, lendo o par (vaga, CV) juntos em vez de comparar vetores separados.

### Por que é diferente do bi-encoder

| | Bi-encoder | Cross-encoder |
|---|---|---|
| Como funciona | `encode(CV)` e `encode(Vaga)` separados → dot product | `encode("[vaga] [SEP] [cv]")` → score direto |
| Velocidade | O(1) na leitura (vetores já salvos) | O(N) — um forward pass por par |
| Precisão | Bom para triagem em massa | Melhor para ordenação fina |
| Captura interações? | Não — "Python na vaga" e "Python no CV" são comparados indiretamente | Sim — vê os dois textos juntos |

### Modelo

Padrão: `BAAI/bge-reranker-base` (~270MB). Configurável via `RERANKER_MODEL`.

Carregado em memória com **lazy load** — só inicializa na primeira chamada ao endpoint `POST /vagas/{id}/rerankar`, não no boot da API.

### Funcionamento

1. Recebe os top-N candidaturas (padrão: 20, via `RERANKER_TOP_N`)
2. Para cada candidatura, extrai o trecho mais relevante do CV via `texto_para_rerank()`: resumo + experiência + habilidades, limitado a **800 chars** (para caber no limite de 512 tokens do modelo junto com o texto da vaga)
3. Forma pares `(texto_requisitos_vaga, trecho_cv)` e passa ao modelo
4. Normaliza os logits do modelo para [0, 1] via **sigmoid**: `1 / (1 + exp(-logit))`
5. Retorna a lista reordenada do maior para o menor score

### Por que é um botão e não automático

O bônus está calculado com os vetores — que ficam salvos no banco e são reutilizáveis.
O reranker produz uma opinião sobre um par específico, que precisa ser recalculada toda vez que a vaga mudar. Rodar para todos os candidatos a cada edição multiplicaria o custo computacional por cada mudança de requisitos.

O botão "Reordenar (IA)" torna esse custo explícito e consciente.

---

## Configuração via `.env`

```env
# Modelo de embedding — mudar exige migração de schema e reprocessamento total
EMBEDDING_MODEL=all-MiniLM-L6-v2   # alternativa: all-mpnet-base-v2 (768d)
EMBEDDING_DIM=384                   # ajustar junto com o modelo

# Cross-encoder reranker
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_TOP_N=20                   # quantos candidatos o reranker processa

# Fonte de dados do market analyzer
MARKET_ANALYZER_SOURCE=kaggle       # "kaggle" | "adzuna" | "ambos"
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

---

## Sumário dos scores

| Score | Escala | Quando calculado | Onde fica |
|---|---|---|---|
| `score_rh` | 0–100 | Após upload do CV | `curriculos.score_rh` |
| `score_mercado` | 0–100 | Após upload do CV | `curriculos.score_mercado` |
| `score_curriculo` | 0–100 | Após upload do CV | `curriculos.score_curriculo` |
| `score_manual` (entrevista RH) | 0–10 | Após entrevista | `entrevistas.score_manual` |
| `score_manual` (entrevista Téc.) | 0–10 | Após entrevista | `entrevistas.score_manual` |
| `score_total` | 0–100 | Após entrevistas | `candidaturas.score_total` |
| `score_rerank` | 0–1 | Sob demanda (botão) | Memória (não persistido) |
