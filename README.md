# SIRS — Sistema Inteligente de Recrutamento e Seleção

Sistema web completo para automação do processo seletivo, combinando NLP semântico em três camadas, análise de mercado em tempo real, extração de features estruturais de currículos e gestão de entrevistas com controle de acesso granular.

---

## Sumário

- [Visão geral](#visão-geral)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Papéis e permissões](#papéis-e-permissões)
- [Pipeline do processo seletivo](#pipeline-do-processo-seletivo)
- [Como o sistema avalia currículos](#como-o-sistema-avalia-currículos)
- [Webhook de importação](#webhook-de-importação)
- [Decisões de design](#decisões-de-design)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Populando o banco](#populando-o-banco)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Endpoints da API](#endpoints-da-api)
- [Frontend — páginas](#frontend--páginas)
- [Testes](#testes)
- [Comandos úteis](#comandos-úteis)

---

## Visão geral

O SIRS automatiza a triagem de candidatos em três camadas de pontuação progressivamente mais precisas:

### Camada 1 — Score curricular (automático, Celery)

O RH faz upload do PDF ou importa via webhook. O sistema segmenta o currículo em seções (experiência, habilidades, educação), vetoriza cada uma e calcula dois componentes:

| Componente | O que mede | Peso padrão |
|---|---|---|
| Aderência à vaga | Combinação de similaridade semântica por seção + bônus estrutural | 60% |
| Aderência ao mercado | Similaridade entre skills do currículo e vetor do mercado | 40% |

```
score_curriculo = (score_rh × 0.60) + (score_mercado × 0.40)
```

O `score_rh` é híbrido: 85% similaridade semântica + 15% bônus estrutural baseado em anos de experiência, nível de senioridade e overlap de habilidades.

### Camada 2 — Entrevistas

RH agenda e registra a entrevista de RH. O gestor técnico pode agendar e registrar a entrevista técnica para as vagas às quais está atribuído. Cada entrevista tem score 0–10, anotações, pontos fortes/fracos e histórico de edições.

### Camada 3 — Score consolidado final

```
score_total = (score_curriculo × 0.50) + (score_entrevista_rh × 0.25) + (score_entrevista_tec × 0.25)
```

Os pesos são configuráveis por vaga.

### Reranking por cross-encoder (sob demanda)

O RH pode acionar o botão "Reordenar (IA)" em qualquer vaga. O sistema aplica um cross-encoder sobre os top-N candidatos — que lê o par (requisitos_vaga, trecho_cv) junto, capturando interações semânticas que o bi-encoder perde. Ver [decisões de design](#decisões-de-design) para entender por que esse passo é manual.

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| **Frontend** | React 18, Vite, Tailwind CSS v4 |
| **NLP / IA (bi-encoder)** | sentence-transformers (`all-MiniLM-L6-v2`, configurável) |
| **NLP / IA (cross-encoder)** | `BAAI/bge-reranker-base` (configurável) |
| **Extração estrutural** | Regex + heurísticas (anos, senioridade, skills) — sem modelo extra |
| **Análise de mercado** | Adzuna API, Kaggle LinkedIn Jobs dataset |
| **Banco de dados** | PostgreSQL 16 + pgvector (vetores de 384 dims) |
| **Filas / background** | Celery 5, Redis 7 |
| **Autenticação** | JWT (python-jose, bcrypt) |
| **Infraestrutura** | Docker, Docker Compose |
| **Testes** | pytest, TestClient (FastAPI), banco de testes isolado por savepoint |

---

## Arquitetura

```
┌──────────────────────────────────────────────────────┐
│                  React SPA (Vite)                    │
│   /vagas  /candidatos  /admin  /candidaturas/:id     │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP /api/*
┌───────────────────────▼──────────────────────────────┐
│               FastAPI (porta 8000)                   │
│  JWT · RBAC por papel e por vaga · REST · Webhook    │
│                                                      │
│  /auth  /vagas  /candidatos  /candidaturas           │
│  /entrevistas  /usuarios  /webhook                   │
└────────┬──────────────────────────┬──────────────────┘
         │ SQLAlchemy               │ .delay()
┌────────▼────────┐       ┌─────────▼──────────────────┐
│  PostgreSQL     │       │       Celery Worker         │
│  + pgvector     │       │                             │
│                 │       │  processar_curriculo        │
│  candidatos     │       │  processar_curriculo_texto  │
│  vagas          │       │  atualizar_mercado_vaga     │
│  candidaturas   │       └─────────┬──────────────────┘
│  curriculos     │                 │
│    vetor_embed  │       ┌─────────▼──────────────────┐
│    vetor_exp    │       │         Motor de IA         │
│    vetor_skills │       │                             │
│  entrevistas    │       │  resume_parser              │
│  usuarios       │       │    PDF → texto → vetores   │
│    rhs_autorizados      │    + segmentação de seções  │
└─────────────────┘       │                             │
                          │  section_extractor          │
         ┌────────────────│    headers + densidade      │
         │                │                             │
┌────────▼────────┐       │  feature_extractor          │
│     Redis       │       │    anos, nível, skills      │
│  (broker +      │       │                             │
│   results)      │       │  matching_engine            │
└─────────────────┘       │    multi-seção + estrutural │
                          │                             │
                          │  reranker (cross-encoder)   │
                          │    sob demanda              │
                          │                             │
                          │  market_analyzer            │
                          │    Kaggle / Adzuna + TF-IDF │
                          └────────────────────────────┘
```

---

## Papéis e permissões

O sistema tem 3 papéis. Além do papel, existe um controle **por vaga**: cada vaga tem um criador e uma lista de analistas autorizados (`rhs_autorizados`). Vagas criadas por admin não têm restrição de acesso.

### Tabela de permissões

| Ação | RH criador / autorizado | Gestor (vaga atribuída) | Admin |
|---|:---:|:---:|:---:|
| Criar vaga | ✓ | — | ✓ |
| Editar vaga (pesos, status, gestores) | ✓ | — | ✓ |
| Visualizar vaga e candidatos | ✓ | ✓ | ✓ |
| Gerenciar analistas autorizados | criador | — | ✓ |
| Aprovar / reprovar triagem | ✓ | — | ✓ |
| Fazer upload de currículo | ✓ | — | ✓ |
| Agendar entrevista RH | ✓ | — | ✓ |
| Agendar entrevista técnica | ✓ | ✓ | ✓ |
| Registrar resultado entrevista RH | ✓ | — | ✓ |
| Registrar resultado entrevista técnica | — | ✓ | ✓ |
| Reprovar após entrevista RH | ✓ | — | ✓ |
| Tomar decisão final | ✓ | ✓ | ✓ |
| Acionar reranking por cross-encoder | ✓ | — | ✓ |
| Gerenciar usuários | — | — | ✓ |

### Modelo de exclusividade por vaga

Quando um analista de RH cria uma vaga, ele torna-se o **criador exclusivo**. Outros RHs não veem a vaga na listagem nem podem editá-la até que o criador os adicione à lista `rhs_autorizados`. O criador não pode remover a si mesmo da lista.

Vagas criadas por Admin não têm `rhs_autorizados` — são abertas a qualquer RH.

---

## Pipeline do processo seletivo

```
Candidato entra
(cadastro RH, webhook JSON/XML, ou POST /candidatos/webhook)
          │
          ▼
       [NOVO]
          │  RH faz upload do PDF  OU  webhook envia curriculo_texto
          ▼
[AGUARDANDO_PROCESSAMENTO]
          │  Celery processa
          ▼
  [PROCESSANDO_CURRICULO]
          │  Embedding gerado, seções vetorizadas, scores calculados
          ▼
   [TRIAGEM_PENDENTE]  ◄── RH analisa ranking
          │
    ┌─────┴──────┐
    ▼            ▼
[REPROVADO   [APROVADO
 TRIAGEM]     TRIAGEM]
                  │  RH agenda entrevista
                  ▼
        [ENTREVISTA_RH_AGENDADA]
                  │  RH registra resultado
                  ▼
         [ENTREVISTA_RH_REALIZADA]
                  │
         ┌────────┴──────────┐
         ▼                   ▼
    [REPROVADO_RH]  [ENTREVISTA_TEC_AGENDADA]  ← RH ou Gestor agenda
                             │  Gestor registra resultado
                             ▼
                    [ENTREVISTA_TEC_REALIZADA]
                             │
                    ┌────────┴──────────┐
                    ▼                   ▼
             [REPROVADO_TEC]  [DECISAO_PENDENTE]
                                        │  RH ou Gestor decide
                             ┌──────────┼──────────┐
                             ▼          ▼           ▼
                       [CONTRATADO] [NAO_       [BANCO
                                    APROVADO]   TALENTOS]
```

Cada transição é registrada em `candidatura.historico` (JSONB) com timestamp, estados anterior/posterior e quem realizou a ação.

---

## Como o sistema avalia currículos

### Pipeline de scoring em três subcamadas

```
                    ┌─────────────────────────────────┐
  TEXTO DO CV  ──►  │   1. section_extractor          │
                    │   Detecta seções por cabeçalho  │
                    │   ou por densidade de keywords  │
                    └──┬──────────────┬───────────────┘
                       │              │
               ┌───────▼──┐   ┌──────▼──────┐
               │  exp_vec  │   │ skills_vec  │
               └───────┬──┘   └──────┬──────┘
                       │              │
                    ┌──▼──────────────▼──────────────┐
   VAGA_VEC  ──►    │   2. matching_engine            │
   MERCADO_VEC ──►  │   Multi-seção:                 │
                    │   45% × sim(exp, vaga)          │
                    │   30% × sim(full_cv, vaga)      │
                    │   25% × sim(skills, mercado)    │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
   TEXTO_CV ──►     │   3. feature_extractor          │
   TEXTO_VAGA ──►   │   Bônus estrutural (±15%):     │
                    │   anos experiência vs requisito │
                    │   nível senioridade             │
                    │   overlap de habilidades        │
                    └──────────────┬─────────────────┘
                                   │
                             score_rh (0–1)
```

O score mercado usa o `vetor_mercado` da vaga (gerado pelo Market Analyzer), que representa as skills mais demandadas no mercado para aquele cargo.

### Reranking sob demanda (cross-encoder)

```
Bi-encoder   →  ordena 500 candidatos  (O(1) — já calculado)
Cross-encoder → reordena top-20        (O(N) — ~3–5s sob demanda)
```

O cross-encoder lê o par `(requisitos_vaga, trecho_cv)` junto em vez de comparar vetores separados. Isso captura interações que o bi-encoder perde — por exemplo, que "sistemas distribuídos" no CV corresponde a "Kafka" na vaga mesmo sem a palavra aparecer.

### Embeddings semânticos vs. TF-IDF

O modelo `all-MiniLM-L6-v2` captura semântica — termos equivalentes ficam próximos no espaço vetorial:

| Par de termos | TF-IDF | Embedding |
|---|:---:|:---:|
| "AWS" × "Amazon Web Services" | 0.00 | ~0.94 |
| "Python dev" × "desenvolvedor backend" | 0.00 | ~0.82 |
| "banco de dados" × "PostgreSQL" | 0.00 | ~0.71 |

### Market Analyzer

Ao criar uma vaga, o sistema detecta a categoria do cargo (tech, direito, RH, engenharia, financeiro, marketing) e coleta dados de:

- **Kaggle** (dataset LinkedIn Jobs, ~120k vagas) — cargos tech
- **Adzuna API** (vagas reais em PT-BR) — outros cargos

Aplica TF-IDF nos textos coletados para extrair as top skills do mercado, gera um vetor médio ponderado e salva como `vaga.vetor_mercado`.

### Currículo por candidatura

Cada candidatura tem seu próprio currículo processado — o candidato pode enviar um CV focado em Python para a vaga de Dev e outro para a vaga de DevOps, sem que um sobrescreva o outro.

---

## Webhook de importação

O endpoint `POST /webhook/importar` aceita JSON ou XML vindos de sistemas externos (ATS, HRIS, SAP).

### Autenticação

Header `X-Webhook-Key: <chave>`. Se `WEBHOOK_SECRET_KEY` não estiver configurado no `.env`, o endpoint é aberto (útil em desenvolvimento).

### Operações por entidade

| Entidade | Comportamento |
|---|---|
| `vagas` | Busca por nome — cria se não existir, ignora se já existir. Dispara `atualizar_mercado_vaga` async. |
| `candidatos` | **Upsert por e-mail** — atualiza campos não-nulos se já existir, cria com `origem="externo"` se não existir. |
| `candidaturas` | Vincula candidato à vaga via `vaga_external_id` ou `vaga_nome`. Não duplica. `origem="externo"` e `fonte=<nome_do_sistema>`. |
| `curriculo_texto` | Cria registro de currículo e dispara `processar_curriculo_texto` (Celery) para vetorizar e calcular scores sem PDF. |

### Isolamento de falhas

Cada candidato roda dentro de um savepoint do banco. Um e-mail inválido em um registro não cancela a importação dos demais — o erro é reportado individualmente na resposta.

### Estrutura JSON

```json
{
  "fonte": "greenhouse",
  "vagas": [
    { "external_id": "v1", "nome": "Dev Python", "requisitos_texto": "Python, FastAPI..." }
  ],
  "candidatos": [
    {
      "external_id": "c1",
      "nome": "João Silva",
      "email": "joao@empresa.com",
      "curriculo_texto": "Desenvolvedor Python com 5 anos...",
      "vaga_external_id": "v1"
    }
  ]
}
```

### Estrutura XML

```xml
<importacao fonte="sap">
  <vagas>
    <vaga external_id="v1">
      <nome>Dev Python</nome>
      <requisitos_texto>Python, FastAPI</requisitos_texto>
    </vaga>
  </vagas>
  <candidatos>
    <candidato external_id="c1" vaga_external_id="v1">
      <nome>João Silva</nome>
      <email>joao@empresa.com</email>
      <curriculo_texto>Desenvolvedor com 5 anos...</curriculo_texto>
    </candidato>
  </candidatos>
</importacao>
```

### Demo

```bash
docker compose exec api python tests/demo_webhook.py        # todos os cenários
docker compose exec api python tests/demo_webhook.py 1      # JSON completo
docker compose exec api python tests/demo_webhook.py 3      # XML
```

---

## Decisões de design

### Por que o reranking é um botão e não automático?

O cross-encoder é **O(N)** — cada par (vaga, CV) exige uma passagem pelo modelo. O bi-encoder é **O(1)** na leitura porque os vetores já estão salvos.

Se o reranking fosse automático, precisaria ser re-executado toda vez que os requisitos da vaga mudassem, os pesos fossem ajustados ou o ranking de mercado fosse atualizado — multiplicando o custo computacional por cada edição.

O bi-encoder gera um **ativo reutilizável** (o vetor, que fica no banco). O cross-encoder gera uma **opinião pontual sobre um par específico** que precisa ser renovada toda vez que qualquer lado muda. O botão manual torna esse custo explícito e consciente.

Além disso, o modelo cross-encoder é carregado em memória somente na primeira chamada (lazy load de ~270 MB). Carregar no boot atrasaria a inicialização de todos os containers sem benefício quando o RH não precisar rerankar.

### Por que o `score_rh` não usa só similaridade semântica?

O embedding capta semântica mas ignora fatos estruturais: "2 anos de experiência" e "15 anos de experiência" ficam próximos se o restante do CV for similar. O bônus estrutural (±15%) corrige isso sem dominar o score:

- Um candidato júnior para uma vaga sênior recebe penalidade no bônus, mesmo com alta similaridade semântica.
- Um candidato com overlap alto de skills recebe bônus mesmo que sua redação seja menos semântica.

O limite de ±15% foi escolhido para que o bônus seja um refinamento, não o determinante.

### Por que vetorizar seções separadas?

O CV de um sênior de 10 anos tem muito texto — contexto, descrições de projetos, histórico completo. Ao comparar o vetor do CV inteiro com o vetor da vaga, o modelo "dilui" a parte relevante (experiência técnica) com ruído (objetivos, hobbies, formato). Vetorizar a seção de Experiência separadamente e dar peso maior a ela na fórmula final melhora a precisão sem precisar de um modelo diferente.

### Por que `origem` está na `Candidatura` e não no `Candidato`?

Uma pessoa pode candidatar-se a múltiplas vagas por caminhos diferentes — uma vaga manualmente pelo RH, outra via webhook do LinkedIn. Colocar `origem` no candidato jogaria fora essa distinção. Na candidatura, cada aplicação carrega seu próprio contexto de origem e fonte.

### Por que a exclusividade de vagas por RH?

Sem controle por criador, qualquer RH poderia ver e editar os pesos, candidatos e entrevistas de vagas que não são suas — criando conflitos em empresas com múltiplos times de recrutamento. O modelo `criado_por_id` + `rhs_autorizados` resolve isso: o criador tem controle total e pode delegar explicitamente, sem que outros RHs entrem em conflito.

Vagas criadas por Admin ficam abertas a todos os RHs por convenção — o admin geralmente cria vagas de estrutura que qualquer analista pode gerenciar.

---

## Pré-requisitos

- Docker Desktop com WSL2 (Windows) ou Docker Engine (Linux/Mac)
- Git

> **Windows:** desenvolva dentro do filesystem do Ubuntu (`~/projetos`), não em `/mnt/c/`. O Docker tem desempenho muito inferior ao acessar o filesystem Windows.

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/JuliaDuran15/SIRS-Sistema-Inteligente-de-Recrutamento-e-Selecao.git sirs
cd sirs
```

### 2. Configurar variáveis de ambiente

```bash
cp backend/.env.example backend/.env
# edite backend/.env conforme necessário
```

### 3. Build e subida

```bash
docker compose up --build
```

> A primeira execução baixa o modelo `all-MiniLM-L6-v2` (~90 MB) e as dependências Python. Pode levar 5–10 minutos. As execuções seguintes são rápidas.
>
> O cross-encoder (`BAAI/bge-reranker-base`, ~270 MB) é baixado na primeira vez que o botão "Reordenar (IA)" for acionado.

### 4. Rodar migrações

```bash
docker compose exec api alembic upgrade head
```

### 5. Verificar

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

| Serviço | URL | Descrição |
|---|---|---|
| Frontend | http://localhost:5173 | React SPA |
| API | http://localhost:8000 | FastAPI REST |
| Docs interativos | http://localhost:8000/docs | Swagger UI |
| Banco | localhost:5432 | PostgreSQL |

---

## Variáveis de ambiente

Arquivo `backend/.env`:

```env
# Banco de dados
DATABASE_URL=postgresql://sirs:sirs123@db:5432/sirs_db

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# JWT — gere com: openssl rand -hex 32
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
ALGORITHM=HS256

# Usuário admin inicial
ADMIN_EMAIL=admin@sirs.com
ADMIN_SENHA=admin123

# ── Modelos de IA ────────────────────────────────────────────────────────────
# Bi-encoder: "all-MiniLM-L6-v2" (384d, padrão) ou "all-mpnet-base-v2" (768d)
# Trocar o modelo exige: alterar EMBEDDING_DIM, rodar migração e reprocessar CVs.
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Cross-encoder (reranker): carregado sob demanda, ~270 MB
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_TOP_N=20    # quantos candidatos o reranker processa por chamada

# ── Webhook ──────────────────────────────────────────────────────────────────
# Deixe vazio para não exigir autenticação (dev). Em produção, defina uma chave.
WEBHOOK_SECRET_KEY=

# ── Market Analyzer ──────────────────────────────────────────────────────────
MARKET_ANALYZER_SOURCE=kaggle   # "kaggle" | "adzuna" | "ambos"

# Adzuna API (opcional — cadastro gratuito em api.adzuna.com)
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
ADZUNA_COUNTRY=br
```

> Para usar o Kaggle como fonte, coloque o arquivo `postings.csv` do [dataset LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) em `backend/data/postings.csv`.

---

## Populando o banco

### Seed completo (dados realistas em todas as etapas)

```bash
docker compose exec api python tests/seed_full.py
```

O seed é idempotente — limpa e repopula. Também cria as extensões e tabelas se não existirem.

O seed completo cria:

- **6 usuários** — 2 RH, 3 gestores técnicos, 1 admin
- **10 vagas** — Python, Full Stack, Dados, DevOps, RH, Direito, Civil, Financeiro, UX/UI, Marketing (com market analysis real)
- **30 candidatos** com formações e perfis variados
- **~55 candidaturas** distribuídas em todas as etapas do pipeline, com currículos processados (scores reais), entrevistas e histórico de transições
- **5 candidaturas** com `origem="externo"` e `fonte="greenhouse"` para demonstração do webhook

Logins após o seed:

| Email | Senha | Papel |
|---|---|---|
| `ana@sirs.com` | `senha123` | RH |
| `bruno@sirs.com` | `senha123` | RH |
| `carlos@sirs.com` | `senha123` | Gestor técnico |
| `daniela@sirs.com` | `senha123` | Gestor técnico |
| `eduardo@sirs.com` | `senha123` | Gestor técnico |
| `admin@sirs.com` | `admin123` | Admin |

---

## Estrutura de pastas

```
sirs/
├── docker-compose.yml
├── docker/
│   ├── Dockerfile.api
│   └── init.sql                 # cria extensão pgvector
│
├── backend/
│   ├── .env
│   ├── pyproject.toml           # pytest config
│   ├── migrations/              # Alembic
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── ai/
│       │   ├── tasks.py             # Celery: processar_curriculo, processar_curriculo_texto,
│       │   │                        #         atualizar_mercado_vaga
│       │   ├── resume_parser.py     # PDF → texto → embedding (modelo configurável)
│       │   │                        # + vetorização por seção
│       │   ├── section_extractor.py # Segmenta CV em: experiência, habilidades, educação, resumo
│       │   │                        # Estratégia: cabeçalhos → fallback por densidade
│       │   ├── matching_engine.py   # Scores: multi-seção, híbrido, consolidado, cross-encoder
│       │   ├── feature_extractor.py # Anos de experiência (explícito + intervalos + fallback),
│       │   │                        # nível de senioridade, overlap de habilidades
│       │   ├── reranker.py          # Cross-encoder (lazy load, sob demanda)
│       │   └── market_analyzer.py   # Kaggle/Adzuna + TF-IDF → vetor de mercado
│       ├── api/
│       │   ├── deps.py
│       │   └── endpoints/
│       │       ├── auth.py
│       │       ├── usuarios.py
│       │       ├── vagas.py         # inclui POST /vagas/{id}/rerankar
│       │       ├── candidatos.py    # GET filtrado por papel (gestor vê só os seus)
│       │       ├── candidaturas.py  # gestor pode tomar decisão final
│       │       ├── entrevistas.py   # gestor pode agendar técnica nas suas vagas
│       │       └── webhook.py       # POST /webhook/importar (JSON + XML)
│       ├── core/
│       │   ├── auth.py              # JWT, hash, guards RBAC
│       │   ├── config.py            # EMBEDDING_MODEL, RERANKER_MODEL, WEBHOOK_SECRET_KEY…
│       │   └── celery_app.py
│       ├── db/
│       │   ├── session.py
│       │   ├── base.py
│       │   └── ensure_admin.py
│       ├── models/
│       │   ├── usuario.py
│       │   ├── vaga.py              # criado_por_id, rhs_autorizados
│       │   ├── candidato.py
│       │   ├── candidatura.py       # origem, fonte, máquina de estados, historico
│       │   ├── curriculo.py         # vetor_embedding, vetor_secao_exp, vetor_secao_skills
│       │   └── entrevista.py
│       └── schemas/
│           ├── vaga.py              # RhsAutorizadosUpdate
│           ├── candidatura.py       # CandidaturaRerankItem
│           └── webhook.py           # ImportacaoPayload, ImportacaoResponse
│
├── frontend/
│   └── src/
│       ├── api.js                   # axios + rerankarVaga, updateRhsAutorizados…
│       ├── pages/
│       │   ├── Vagas.jsx            # botões de status só para RHs autorizados
│       │   ├── VagaDetalhe.jsx      # "Analistas autorizados" + "Reordenar (IA)"
│       │   ├── EntrevistaDetalhe.jsx # currículo visível ao gestor (read-only),
│       │   │                         # reprovar RH, decisão do gestor
│       │   ├── Candidatos.jsx
│       │   └── AdminUsuarios.jsx
│       └── index.css                # light mode com tokens de cor ajustados
│
└── backend/tests/
    ├── conftest.py              # DB isolado por savepoint, factories
    ├── seed_full.py             # seed idempotente (cria tabelas se necessário)
    ├── demo_webhook.py          # simula sistema externo enviando dados
    ├── test_auth.py
    ├── test_usuarios.py
    ├── test_vagas.py            # inclui TestRhsAutorizados
    ├── test_candidatos.py
    ├── test_candidaturas.py
    ├── test_entrevistas.py      # gestor agenda técnica, gestor decide
    ├── test_webhook.py          # JSON, XML, upsert, erros parciais, origem
    ├── test_matching_engine.py
    ├── test_market_analyzer.py
    └── test_feature_extractor.py # anos de experiência (explícito, intervalos, sobreposição),
                                  # nível de senioridade, skills, bônus estrutural
```

---

## Endpoints da API

Documentação interativa: `http://localhost:8000/docs`

### Auth
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/token` | público | Login OAuth2 password flow |
| PATCH | `/auth/senha` | autenticado | Alterar senha |
| POST | `/auth/esqueceu-senha` | público | Solicitar reset por e-mail |
| POST | `/auth/resetar-senha` | público | Resetar com token |

### Usuários
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/usuarios/` | admin | Criar usuário |
| GET | `/usuarios/` | autenticado | Listar usuários ativos |
| DELETE | `/usuarios/{id}` | admin | Desativar usuário |

### Vagas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/vagas/` | RH, admin | Criar vaga (dispara market analysis) |
| GET | `/vagas/` | autenticado | Listar vagas (filtrado por papel e autorização) |
| GET | `/vagas/{id}` | autenticado | Detalhes |
| PATCH | `/vagas/{id}/pesos` | RH autorizado, admin | Ajustar pesos do score |
| PATCH | `/vagas/{id}/status` | RH autorizado, admin | Abrir / pausar / fechar |
| PATCH | `/vagas/{id}/gestores` | RH autorizado, admin | Atribuir gestores técnicos |
| PATCH | `/vagas/{id}/rhs-autorizados` | criador, admin | Gerenciar analistas com acesso |
| POST | `/vagas/{id}/rerankar` | RH autorizado, admin | Reordenar top-N por cross-encoder |
| POST | `/vagas/{id}/analisar-mercado` | RH autorizado, admin | Re-executar análise de mercado |
| DELETE | `/vagas/{id}` | admin | Fechar vaga |

### Candidatos
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/candidatos/` | RH, admin | Cadastrar candidato |
| POST | `/candidatos/webhook` | público | Receber candidato de sistema externo (legado) |
| GET | `/candidatos/` | autenticado | Listar (gestor vê só candidatos das suas vagas) |
| GET | `/candidatos/{id}` | autenticado | Perfil |
| PATCH | `/candidatos/{id}` | RH, admin | Atualizar dados |

### Candidaturas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/candidaturas/` | RH, admin | Vincular candidato a vaga |
| GET | `/candidaturas/` | autenticado | Listar (filtro: `?vaga_id=` ou `?candidato_id=`) |
| GET | `/candidaturas/{id}` | autenticado | Detalhes + candidato + currículo |
| PATCH | `/candidaturas/{id}/status` | RH / gestor (só decisão final) / admin | Avançar no pipeline |
| POST | `/candidaturas/{id}/curriculo` | RH autorizado, admin | Upload PDF |
| GET | `/candidaturas/{id}/curriculo` | autenticado | Texto extraído do currículo |

### Entrevistas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/entrevistas/` | RH autorizado / gestor (só técnica) / admin | Agendar |
| PATCH | `/entrevistas/{id}/resultado` | RH (tipo rh) / gestor (tipo técnica) / admin | Registrar resultado |
| PATCH | `/entrevistas/{id}/anotacoes` | RH (tipo rh) / gestor da vaga (tipo técnica) / admin | Editar anotações |
| GET | `/entrevistas/candidatura/{id}` | autenticado | Listar entrevistas de uma candidatura |

### Webhook
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/webhook/importar` | `X-Webhook-Key` ou aberto | Importar vagas/candidatos/currículos (JSON ou XML) |

---

## Frontend — páginas

| Rota | Acesso | Descrição |
|---|---|---|
| `/login` | público | Login |
| `/` | autenticado | Lista de vagas (filtrada por papel e autorização) |
| `/vagas/:id` | autenticado | Ranking de candidatos, market skills, pesos, gestores, analistas autorizados, botão "Reordenar (IA)" |
| `/candidatos` | autenticado | Lista de candidatos (gestor vê só os das suas vagas) |
| `/candidaturas/:id/entrevistas` | autenticado | Currículo (scores + leitura para gestor), entrevistas, decisão final (RH ou gestor) |
| `/admin` | admin | Gerenciar usuários |

---

## Testes

Os testes usam um banco PostgreSQL dedicado (`sirs_test_db`) com isolamento por savepoint — cada teste roda em um savepoint que é desfeito ao final, sem afetar o banco principal.

Celery tasks e o modelo de embeddings são mockados globalmente para que os testes de API sejam rápidos.

### Rodar todos os testes

```bash
docker compose exec api python -m pytest tests/ -v
```

### Rodar por módulo

```bash
docker compose exec api python -m pytest tests/test_vagas.py -v
docker compose exec api python -m pytest tests/test_feature_extractor.py -v
docker compose exec api python -m pytest tests/test_webhook.py -v
docker compose exec api python -m pytest tests/test_analytics.py tests/test_fluxo_completo.py tests/test_candidaturas.py::TestTriagemEmLote -v
```

### Cobertura por módulo

| Arquivo | Testes | O que cobre |
|---|:---:|---|
| `test_matching_engine.py` | 29 | Scores RH, mercado, multi-seção, XAI, score final |
| `test_feature_extractor.py` | 49 | Anos de experiência (3 estratégias), senioridade, skills, bônus estrutural, intervalos com sobreposição |
| `test_market_analyzer.py` | 26 | Detecção de categoria, extração de skills, TF-IDF |
| `test_auth.py` | 19 | Login, hash/token, guards RBAC |
| `test_usuarios.py` | 20 | CRUD + guards admin |
| `test_vagas.py` | 43 | CRUD + exclusividade RH + rhs_autorizados + market analysis |
| `test_candidatos.py` | 21 | CRUD + webhook + gestor filtra candidatos |
| `test_candidaturas.py` | 25 | CRUD + máquina de estados + upload PDF + gestor decide |
| `test_entrevistas.py` | 37 | Gestor agenda técnica, registrar resultado, permissões por vaga |
| `test_webhook.py` | 22 | JSON, XML, upsert, erros parciais, origem na candidatura, API key |
| **Total** | **306** | |

---

## Comandos úteis

```bash
# Subir os serviços
docker compose up -d

# Logs em tempo real
docker compose logs api -f
docker compose logs worker -f

# Acessar o banco de dados
docker compose exec db psql -U sirs -d sirs_db

# Criar nova migração após alterar um model
docker compose exec api alembic revision --autogenerate -m "descricao"
docker compose exec api alembic upgrade head

# Reverter última migração
docker compose exec api alembic downgrade -1

# Rebuildar a imagem da API
docker compose up --build api

# Reiniciar worker (necessário após mudar código de tasks ou modelos de IA)
docker compose restart worker

# Rodar o seed completo (limpa e repopula)
docker compose exec api python tests/seed_full.py

# Demonstrar o webhook com dados realistas
docker compose exec api python tests/demo_webhook.py

# Ver workers Celery ativos
docker compose exec worker celery -A app.core.celery_app inspect active

# Ver filas pendentes no Redis
docker compose exec redis redis-cli llen celery
```

---

## Contexto acadêmico

Desenvolvido como Trabalho de Conclusão de Curso, propondo uma abordagem em camadas para triagem de currículos que combina:

1. **Similaridade semântica** por seção de documento (embedding por seção > embedding do documento inteiro)
2. **Extração estrutural baseada em regras** para sinais que embeddings ignoram (anos de experiência, nível de senioridade)
3. **Two-stage retrieval** (bi-encoder → cross-encoder) para balancear eficiência computacional e precisão na ordenação final

A abordagem contorna a ausência de datasets rotulados através de similaridade vetorial não supervisionada e análise de mercado em tempo real como proxy de relevância.

**Referências principais:**
- Reimers & Gurevych (2019) — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
- Nogueira & Cho (2019) — Passage Re-ranking with BERT
- Salton & Buckley (1988) — Term-weighting approaches in automatic text retrieval
