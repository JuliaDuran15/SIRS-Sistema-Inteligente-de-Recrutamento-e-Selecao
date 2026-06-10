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

O RH faz upload do PDF ou importa via webhook. O sistema segmenta o currículo em seções (experiência, habilidades, educação), vetoriza cada uma e calcula dois componentes semânticos puros, depois aplica um bônus estrutural ao score combinado:

| Componente | O que mede | Peso padrão |
|---|---|---|
| Aderência à vaga | Similaridade semântica por seção (60% seção exp + 40% CV completo) | 60% |
| Aderência ao mercado | Similaridade entre skills do currículo e vetor do mercado | 40% |

```
score_curriculo = clamp(
  score_rh × peso_rh + score_mercado × peso_mercado + bonus_estrutural,
  0, 1
) × 100
```

O `bonus_estrutural` (±0.25) é calculado pelo `feature_extractor` a partir de três sinais:

| Sinal | Intervalo | Comportamento |
|---|---|---|
| Experiência | ±0.08 | Escalado pelo overlap de skills — exp irrelevante vale menos |
| Senioridade | ±0.15 | Penalidade proporcional ao gap de nível |
| Skills overlap | −0.15 a +0.08 | **Penalidade de −0.15 quando 0 skills em comum**, bônus ponderado por proficiência |

A proficiência de cada skill é detectada por contexto (janela ±70 chars): `básico/iniciante → 0.3`, padrão → `1.0`, `avançado/expert → 1.3`.

### Camada 2 — Entrevistas

RH agenda e registra a entrevista de RH. O gestor técnico pode agendar e registrar a entrevista técnica para as vagas às quais está atribuído. Cada entrevista tem score 0–10, anotações, pontos fortes/fracos e histórico de edições.

### Camada 3 — Score consolidado final

```
score_total = (score_curriculo × 0.50) + (score_entrevista_rh × 0.25) + (score_entrevista_tec × 0.25)
```

Os pesos são configuráveis por vaga.

### Reranking por cross-encoder (sob demanda)

O RH pode acionar o botão "Reordenar (IA)" em qualquer vaga. O sistema aplica um cross-encoder sobre os top-N candidatos — que lê o par (requisitos_vaga, trecho_cv) junto, capturando interações semânticas que o bi-encoder perde.

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| **Frontend** | React 18, Vite, Tailwind CSS v4 |
| **NLP / IA (bi-encoder)** | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384d, multilingual PT/EN/ES) |
| **NLP / IA (cross-encoder)** | `BAAI/bge-reranker-base` (configurável) |
| **Extração estrutural** | Regex + heurísticas (anos, senioridade, skills, proficiência) — sem modelo extra |
| **Análise de mercado** | Adzuna API, Kaggle LinkedIn Jobs dataset |
| **Banco de dados** | PostgreSQL 16 + pgvector (vetores de 384 dims) |
| **Filas / background** | Celery 5, Redis 7 |
| **Autenticação** | JWT (python-jose, bcrypt) com tokens de reset single-use |
| **Infraestrutura** | Docker, Docker Compose |
| **Testes** | pytest, TestClient (FastAPI), banco de testes isolado por savepoint |

---

## Arquitetura

```
┌──────────────────────────────────────────────────────┐
│                  React SPA (Vite)                    │
│  /vagas  /candidatos  /dashboard  /auditoria         │
│  /admin  /candidaturas/:id  /perfil                  │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP /api/*
┌───────────────────────▼──────────────────────────────┐
│               FastAPI (porta 8000)                   │
│  JWT · RBAC por papel e por vaga · REST · Webhook    │
│                                                      │
│  /auth  /vagas  /candidatos  /candidaturas           │
│  /entrevistas  /usuarios  /analytics  /webhook       │
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
│  usuarios       │       │    PDF → texto → vetores    │
│    historico    │       │    + segmentação de seções  │
└─────────────────┘       │                             │
                          │  section_extractor          │
         ┌────────────────│    headers + densidade      │
         │                │                             │
┌────────▼────────┐       │  feature_extractor          │
│     Redis       │       │    anos, nível, skills,     │
│  (broker +      │       │    proficiência             │
│   results)      │       │                             │
└─────────────────┘       │  matching_engine            │
                          │    multi-seção + estrutural  │
                          │    bônus aplicado ao final  │
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
| Ver auditoria completa do sistema | — | — | ✓ |

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
          │  → e-mail "CV processado" enviado ao RH (se SMTP configurado)
          ▼
   [TRIAGEM_PENDENTE]  ◄── RH analisa ranking e comparação lado a lado
          │
    ┌─────┴──────┐
    ▼            ▼
[REPROVADO   [APROVADO
 TRIAGEM]     TRIAGEM]
    │               │  → e-mail "resultado da triagem" enviado ao RH
    │               │  RH agenda entrevista
    │               ▼
    │       [ENTREVISTA_RH_AGENDADA]
    │               │  → e-mail "entrevista agendada" enviado ao entrevistador
    │               │  RH registra resultado
    │               ▼
    │        [ENTREVISTA_RH_REALIZADA]
    │               │
    │      ┌────────┴──────────┐
    │      ▼                   ▼
    │ [REPROVADO_RH]  [ENTREVISTA_TEC_AGENDADA]  ← RH ou Gestor agenda
    │                          │  → e-mail "entrevista agendada"
    │                          │  Gestor registra resultado
    │                          ▼
    │                 [ENTREVISTA_TEC_REALIZADA]
    │                          │
    │                 ┌────────┴──────────┐
    │                 ▼                   ▼
    │          [REPROVADO_TEC]  [DECISAO_PENDENTE]
    │                                     │  RH ou Gestor decide
    │                          ┌──────────┼──────────┐
    │                          ▼          ▼           ▼
    └──────────►         [CONTRATADO] [NAO_       [BANCO
                                      APROVADO]   TALENTOS]
```

Cada transição é registrada em `candidatura.historico` (JSONB) com timestamp, estados anterior/posterior e quem realizou a ação. O log completo é acessível na página de Auditoria (admin).

---

## Como o sistema avalia currículos

### Extração de features estruturais (`feature_extractor`)

O `feature_extractor` usa regex + heurísticas para extrair sinais que embeddings ignoram:

**Anos de experiência** — 3 estratégias em ordem de prioridade:
1. Declaração explícita: "8 anos de experiência"
2. Intervalos de datas: `2015–2019` + `2019–2023` = 8 anos (com merge de sobreposições)
3. Fallback conservador: menor ano detectado → span / 1.4

**Nível de senioridade** — detecta por keywords: `trainee (0)`, `júnior (1)`, `pleno (2)`, `sênior (3)`, `lead/staff (4)`, `gestão (5)`, `direção (6)`

**Skills técnicas** — catálogo de 100+ skills com normalização de aliases (ex: `k8s → kubernetes`, `next.js → nextjs`, `devops → ci/cd`)

**Proficiência por skill** — janela de ±70 chars ao redor de cada menção:
- Modificadores básicos (`básico`, `iniciante`, `noções`) → peso `0.3`
- Sem modificador → peso `1.0`
- Modificadores avançados (`avançado`, `expert`, `domínio`, `sólido`) → peso `1.3`

### Bônus estrutural

O bônus é calculado **antes** dos scores semânticos e aplicado ao score combinado final:

```python
# 1. Skills overlap (calculado primeiro — condiciona os demais)
if overlap == 0 and hab_req:
    bonus -= 0.15        # penalidade por irrelevância completa
else:
    bonus += overlap_ponderado * 0.08   # overlap ponderado por proficiência

# 2. Experiência (escalada pelo overlap — exp irrelevante vale menos)
escala = max(overlap, 0.3) se há skills na vaga, senão 1.0
if ratio >= 1.0:   bonus += 0.08 * escala
if ratio >= 0.7:   bonus += 0.03 * escala
if ratio < 0.35:   bonus -= 0.10        # penalidade não escalada

# 3. Senioridade
diff == 0:   bonus += 0.07   # nível exato
diff == +1:  bonus += 0.03   # um acima (ok)
diff > +1:   bonus -= 0.01   # overqualification
diff == -1:  bonus -= 0.05
diff == -2:  bonus -= 0.10
diff <= -3:  bonus -= 0.15   # mismatch severo

bonus = clamp(bonus, -0.25, +0.25)
```

### Pipeline de scoring completo

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
   MERCADO_VEC ──►  │   score_rh:                    │
                    │   60% × sim(exp_vec, vaga)      │
                    │   40% × sim(full_cv, vaga)      │
                    │                                 │
                    │   score_mercado:                │
                    │   60% × sim(skills, mercado)    │
                    │   40% × sim(full_cv, mercado)   │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
   TEXTO_CV ──►     │   3. feature_extractor          │
   TEXTO_VAGA ──►   │   bonus_estrutural (±0.25)     │
                    └──────────────┬─────────────────┘
                                   │
                    score_curriculo = clamp(
                      score_rh × peso_rh
                    + score_mercado × peso_mercado
                    + bonus_estrutural, 0, 1) × 100
```

### Reranking sob demanda (cross-encoder)

```
Bi-encoder   →  ordena todos os candidatos  (O(1) — vetores já calculados)
Cross-encoder → reordena top-N             (O(N) — ~3–5s sob demanda)
```

O cross-encoder lê o par `(requisitos_vaga, trecho_cv)` junto, capturando interações semânticas que o bi-encoder perde.

---

## Webhook de importação

O endpoint `POST /webhook/importar` aceita JSON ou XML vindos de sistemas externos (ATS, HRIS, SAP).

### Autenticação

Header `X-Webhook-Key: <chave>`. Se `WEBHOOK_SECRET_KEY` não estiver configurado no `.env`, o endpoint é aberto (útil em desenvolvimento).

### Operações por entidade

| Entidade | Comportamento |
|---|---|
| `vagas` | Busca por nome — cria se não existir, ignora se já existir. Dispara `atualizar_mercado_vaga` async. |
| `candidatos` | **Upsert por e-mail** — atualiza campos não-nulos se já existir. `origem="externo"` e `fonte=<nome_do_sistema>`. |
| `candidaturas` | Vincula candidato à vaga via `vaga_external_id` ou `vaga_nome`. Não duplica. |
| `curriculo_texto` | Cria registro de currículo e dispara `processar_curriculo_texto` (Celery) para vetorizar e calcular scores sem PDF. |

### Isolamento de falhas

Cada candidato roda dentro de um savepoint do banco. Um erro individual não cancela a importação dos demais — é reportado na lista `erros` da resposta.

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

### Demo

```bash
docker compose exec api python tests/demo_webhook.py        # todos os cenários
docker compose exec api python tests/demo_webhook.py 1      # JSON completo
docker compose exec api python tests/demo_webhook.py 3      # XML
```

---

## Decisões de design

### Por que o reranking é um botão e não automático?

O cross-encoder é **O(N)** — cada par (vaga, CV) exige uma passagem pelo modelo. O bi-encoder é **O(1)** na leitura porque os vetores já estão salvos. Se o reranking fosse automático, precisaria ser re-executado a cada edição de requisitos, pesos ou atualização de mercado. O botão torna esse custo explícito.

O modelo cross-encoder é carregado em memória somente na primeira chamada (lazy load de ~270 MB), evitando atraso na inicialização dos containers.

### Por que o bônus estrutural é aplicado ao score combinado e não só ao score_rh?

O `bonus_estrutural` corrige sinais que os embeddings ignoram (anos de experiência, nível, overlap de skills). Aplicá-lo ao score final garante que ele influencie o resultado independentemente dos pesos `peso_rh` e `peso_mercado` configurados na vaga — uma vaga com `peso_rh=0` ainda se beneficia do sinal estrutural.

### Por que experiência irrelevante é escalada pelo overlap de skills?

Um Product Manager com 5 anos de experiência candidatando-se a uma vaga DevOps recebia `+0.08` de bônus de experiência simplesmente por ter os anos exigidos. Como nenhuma das skills é relevante (0 overlap), esses anos não deveriam contar. A escala por overlap corrige isso: `bonus_exp *= max(overlap, 0.3)`.

### Por que tokens de reset de senha têm single-use?

O JWT garante expiração (1 hora), mas sem controle adicional o mesmo token poderia ser usado múltiplas vezes dentro da janela. A solução usa um **fingerprint do hash atual da senha** embutido no token (`fph = sha256(senha_hash)[:16]`). Quando a senha é redefinida, o hash muda, tornando o fingerprint do token antigo inválido automaticamente — sem precisar de banco de tokens revogados.

### Por que o `score_rh` não usa só similaridade semântica?

O embedding capta semântica mas ignora fatos estruturais: "2 anos de experiência" e "15 anos de experiência" ficam próximos se o restante do CV for similar. O bônus estrutural (±25%) corrige isso sem dominar o score.

### Por que vetorizar seções separadas?

O CV de um sênior tem muito texto — ao comparar o vetor inteiro com a vaga, a parte relevante (experiência técnica) é diluída com ruído (objetivos, hobbies). Vetorizar a seção de Experiência separadamente e dar peso maior (60%) melhora a precisão sem precisar de um modelo diferente.

### Por que `origem` está na `Candidatura` e não no `Candidato`?

Uma pessoa pode candidatar-se a múltiplas vagas por caminhos diferentes — uma manualmente, outra via webhook. Colocar `origem` no candidato perderia essa distinção.

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

> A primeira execução baixa o modelo `paraphrase-multilingual-MiniLM-L12-v2` (~120 MB) e as dependências Python. O cross-encoder (`BAAI/bge-reranker-base`, ~270 MB) é baixado na primeira vez que o botão "Reordenar (IA)" for acionado.

### 4. Rodar migrações

```bash
docker compose exec api alembic upgrade heads
```

### 5. Verificar

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Docs interativos | http://localhost:8000/docs |

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

# ── Modelos de IA ─────────────────────────────────────────────────────────────
# Bi-encoder 384d (multilingual PT/EN/ES — padrão):
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384
# Para trocar o modelo: altere EMBEDDING_DIM, crie migração e reprocesse CVs.

# Cross-encoder (reranker): carregado sob demanda
RERANKER_MODEL=BAAI/bge-reranker-base
RERANKER_TOP_N=20

# ── E-mail transacional ───────────────────────────────────────────────────────
# Deixe vazio para desabilitar. Sem SMTP, o link de reset é retornado na resposta.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
FRONTEND_URL=http://localhost:5173

# ── Webhook ───────────────────────────────────────────────────────────────────
# Deixe vazio para não exigir autenticação (dev). Em produção, defina uma chave.
WEBHOOK_SECRET_KEY=

# ── Market Analyzer ───────────────────────────────────────────────────────────
MARKET_ANALYZER_SOURCE=kaggle   # "kaggle" | "adzuna" | "ambos"
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
ADZUNA_COUNTRY=br
```

> Para usar o Kaggle como fonte, coloque o arquivo `postings.csv` do [dataset LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) em `backend/data/postings.csv`.

---

## Populando o banco

```bash
docker compose exec api python tests/seed_full.py
```

O seed cria:

- **6 usuários** — 2 RH, 3 gestores técnicos, 1 admin
- **10 vagas** — Python, Full Stack, Dados, DevOps, RH, Direito, Civil, Financeiro, UX/UI, Marketing
- **30 candidatos** com perfis variados
- **~55 candidaturas** em todas as etapas do pipeline, com scores reais, entrevistas e histórico

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
│   └── init.sql
│
├── backend/
│   ├── .env
│   ├── pyproject.toml
│   ├── migrations/versions/
│   └── app/
│       ├── ai/
│       │   ├── tasks.py             # Celery: processar_curriculo, processar_curriculo_texto,
│       │   │                        #         atualizar_mercado_vaga
│       │   ├── resume_parser.py     # PDF → texto → embedding (multilingual-MiniLM-L12-v2)
│       │   │                        # + vetorização por seção
│       │   ├── section_extractor.py # Segmenta CV: experiência, habilidades, educação, resumo
│       │   ├── matching_engine.py   # Scores semânticos puros (multi-seção)
│       │   │                        # bonus_estrutural aplicado ao score combinado final
│       │   ├── feature_extractor.py # Anos (3 estratégias), senioridade, skills + proficiência,
│       │   │                        # bônus com penalidade por 0 overlap e escala por relevância
│       │   ├── reranker.py          # Cross-encoder (lazy load, sob demanda) + logging detalhado
│       │   └── market_analyzer.py   # Kaggle/Adzuna + TF-IDF → vetor de mercado; blacklist EEO/benefits
│       ├── api/endpoints/
│       │   ├── auth.py              # Login, reset senha single-use (fingerprint do hash)
│       │   ├── vagas.py             # PATCH /requisitos (editar vaga + recalc scores/explicações)
│       │   ├── candidatos.py        # GET com busca (nome/e-mail) + paginação + filtros
│       │   ├── candidaturas.py      # Pipeline completo + triagem em lote; fix JSONB mutation tracking
│       │   ├── entrevistas.py       # Agendamento + resultado + e-mails transacionais
│       │   ├── analytics.py         # Resumo, funil, scores, auditoria (admin)
│       │   └── webhook.py           # POST /webhook/importar (JSON + XML)
│       ├── core/
│       │   ├── auth.py              # JWT, hash, guards RBAC
│       │   ├── email.py             # reset_senha, cv_processado, entrevista_agendada,
│       │   │                        # triagem_resultado
│       │   └── config.py
│       └── models/
│           ├── usuario.py
│           ├── vaga.py
│           ├── candidato.py
│           ├── candidatura.py       # historico JSONB completo
│           ├── curriculo.py         # vetor_embedding, vetor_secao_exp, vetor_secao_skills
│           └── entrevista.py
│
├── frontend/src/
│   ├── api.js
│   ├── pages/
│   │   ├── VagaDetalhe.jsx          # Ranking, pesos, gestores, Reordenar (IA),
│   │   │                            # triagem em lote, comparação lado a lado, editar vaga (RH/admin)
│   │   ├── CandidatoDetalhe.jsx     # Perfil, candidaturas e breakdown de score (ExplicacaoScore)
│   │   ├── Candidatos.jsx           # Busca por nome/e-mail, filtro origem, paginação
│   │   ├── EntrevistaDetalhe.jsx    # Scores + currículo, entrevistas, audit trail
│   │   ├── Auditoria.jsx            # Log completo de ações (apenas admin) + botão atualizar
│   │   ├── Dashboard.jsx
│   │   └── AdminUsuarios.jsx
│   ├── components/
│   │   ├── ExplicacaoScore.jsx      # Breakdown de score reutilizável (VagaDetalhe + CandidatoDetalhe)
│   │   ├── ComparacaoCandidatos.jsx # Modal de comparação lado a lado (2–3 candidatos)
│   │   └── Layout.jsx               # Sidebar com link Auditoria para admin
│   └── index.css                    # Tema claro: paleta cream/quente, sem branco puro
│
└── backend/tests/
    ├── conftest.py
    ├── seed_full.py
    ├── test_feature_extractor.py    # inclui TestProficiencia (13 testes)
    ├── test_ai_curriculo.py
    ├── test_novos_curriculos.py     # 35 testes — DevOps, Frontend, QA, Java, PM
    └── ...
```

---

## Endpoints da API

Documentação interativa: `http://localhost:8000/docs`

### Auth
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/token` | público | Login OAuth2 |
| PATCH | `/auth/senha` | autenticado | Alterar senha |
| POST | `/auth/esqueceu-senha` | público | Solicitar reset (token válido 1h, single-use) |
| POST | `/auth/resetar-senha` | público | Resetar com token |

### Vagas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/vagas/` | RH, admin | Criar vaga |
| GET | `/vagas/` | autenticado | Listar (filtrado por papel e autorização) |
| PATCH | `/vagas/{id}/requisitos` | RH autorizado, admin | Editar nome e/ou requisitos; recalcula scores e explicações |
| PATCH | `/vagas/{id}/pesos` | RH autorizado, admin | Ajustar pesos do score; recalcula scores e explicações |
| PATCH | `/vagas/{id}/gestores` | RH autorizado, admin | Atribuir gestores técnicos |
| PATCH | `/vagas/{id}/rhs-autorizados` | criador, admin | Gerenciar analistas |
| POST | `/vagas/{id}/rerankar` | RH autorizado, admin | Reordenar top-N por cross-encoder |
| POST | `/vagas/{id}/analisar-mercado` | RH autorizado, admin | Re-executar análise de mercado |
| GET | `/vagas/{id}/exportar` | RH autorizado, admin | Exportar candidatos como CSV |

### Candidatos
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/candidatos/` | autenticado | Listar com busca (`?q=`), filtro origem, paginação (`?limit=&offset=`) |
| POST | `/candidatos/` | RH, admin | Cadastrar |
| PATCH | `/candidatos/{id}` | RH, admin | Atualizar |

### Candidaturas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/candidaturas/` | RH, admin | Vincular candidato a vaga |
| PATCH | `/candidaturas/{id}/status` | RH / gestor (decisão final) / admin | Avançar no pipeline |
| POST | `/candidaturas/triagem-em-lote` | RH, admin | Aprovar/reprovar múltiplos |
| POST | `/candidaturas/{id}/curriculo` | RH autorizado, admin | Upload PDF |

### Entrevistas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/entrevistas/` | RH autorizado / gestor (técnica) / admin | Agendar (dispara e-mail) |
| PATCH | `/entrevistas/{id}/resultado` | RH / gestor / admin | Registrar resultado |

### Analytics
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/analytics/resumo` | autenticado | Cards do dashboard |
| GET | `/analytics/funil` | autenticado | Funil por vaga |
| GET | `/analytics/scores` | autenticado | Distribuição de scores |
| GET | `/analytics/auditoria` | **admin** | Log completo de transições (`?vaga_id=&ator=&para=&limit=&offset=`) |

### Webhook
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/webhook/importar` | `X-Webhook-Key` ou aberto | Importar vagas/candidatos/currículos (JSON ou XML) |

---

## Frontend — páginas

| Rota | Acesso | Descrição |
|---|---|---|
| `/login` | público | Login |
| `/` | autenticado | Lista de vagas |
| `/vagas/:id` | autenticado | Ranking, market skills, pesos, triagem em lote, **comparação lado a lado**, editar vaga (RH/admin) |
| `/vagas/:id/kanban` | autenticado | Visão Kanban do pipeline |
| `/candidatos` | autenticado | Lista com busca, filtro e paginação |
| `/candidatos/:id` | autenticado | Perfil, histórico de candidaturas e **breakdown de score** |
| `/candidaturas/:id/entrevistas` | autenticado | Scores, currículo, entrevistas, audit trail |
| `/dashboard` | autenticado | Funil, histograma de scores, cards de resumo |
| `/admin` | **admin** | Gerenciar usuários |
| `/auditoria` | **admin** | Log completo de todas as ações no sistema |
| `/perfil` | autenticado | Alterar senha |

---

## Testes

Os testes usam um banco PostgreSQL dedicado (`sirs_test_db`) com isolamento por savepoint. Celery tasks e o modelo de embeddings são mockados para que os testes de API sejam rápidos.

```bash
# Todos os testes
docker compose exec api pytest tests/ -v

# Só os testes de IA (sem embedding real)
docker compose exec api pytest tests/test_feature_extractor.py tests/test_ai_curriculo.py tests/test_novos_curriculos.py -v

# Testes com embedding real (lentos — ~30s na 1ª execução)
docker compose exec api pytest tests/test_ai_curriculo.py tests/test_novos_curriculos.py -m slow -s -v

# Relatório detalhado de scoring (imprime breakdown completo)
docker compose exec api pytest tests/test_novos_curriculos.py::TestPipelineNovos::test_relatorio_completo -m slow -s

# Relatório de proficiência
docker compose exec api pytest tests/test_feature_extractor.py::TestProficiencia::test_relatorio_proficiencia -s
```

### Cobertura por módulo

| Arquivo | Testes | O que cobre |
|---|:---:|---|
| `test_feature_extractor.py` | 62 | Anos (3 estratégias), senioridade, skills, proficiência (básico/avançado/janela), bônus estrutural com penalidade de 0 overlap |
| `test_ai_curriculo.py` | 34 | Pipeline completo com 5 CVs × 2 vagas: features, bônus, scores semânticos, XAI |
| `test_novos_curriculos.py` | 35 | 5 perfis novos (DevOps, Frontend, QA, Java, PM) × 2 vagas, relatório detalhado |
| `test_matching_engine.py` | 29 | Scores RH, mercado, multi-seção, XAI, score final |
| `test_market_analyzer.py` | 26 | Detecção de categoria, extração de skills, TF-IDF |
| `test_reranker.py` | 17 | Cross-encoder unidade (ordenação, sigmoid, top-n, fallback em erro) + endpoint (auth, 404, score_rerank, logging) |
| `test_auth.py` | 19 | Login, hash/token, guards RBAC |
| `test_vagas.py` | 43 | CRUD + exclusividade RH + rhs_autorizados |
| `test_candidatos.py` | 21 | CRUD + webhook + gestor filtra |
| `test_candidaturas.py` | 25 | CRUD + máquina de estados + triagem em lote |
| `test_entrevistas.py` | 37 | Permissões por papel e por vaga |
| `test_webhook.py` | 22 | JSON, XML, upsert, erros parciais, origem |

---

## Comandos úteis

```bash
# Subir os serviços
docker compose up -d

# Logs em tempo real
docker compose logs api -f
docker compose logs worker -f

# Acessar o banco
docker compose exec db psql -U sirs -d sirs_db

# Aplicar migrações
docker compose exec api alembic upgrade heads

# Criar nova migração
docker compose exec api alembic revision --autogenerate -m "descricao"

# Reverter última migração
docker compose exec api alembic downgrade -1

# Seed completo (limpa e repopula)
docker compose exec api python tests/seed_full.py

# Demonstrar webhook
docker compose exec api python tests/demo_webhook.py

# Reiniciar worker (necessário após alterar tasks ou modelos)
docker compose restart worker

# Ver workers Celery ativos
docker compose exec worker celery -A app.core.celery_app inspect active
```

---

## Contexto acadêmico

Desenvolvido como Trabalho de Conclusão de Curso, propondo uma abordagem em camadas para triagem de currículos que combina:

1. **Similaridade semântica multilingual por seção** — embedding por seção de documento supera embedding do documento inteiro; modelo multilingual captura CVs em PT misturado com inglês técnico
2. **Extração estrutural baseada em regras** — anos de experiência, nível de senioridade, overlap de skills com proficiência, penalização de experiência irrelevante
3. **Two-stage retrieval** — bi-encoder (O(1)) → cross-encoder (O(N) sob demanda) para balancear eficiência e precisão

A abordagem contorna a ausência de datasets rotulados através de similaridade vetorial não supervisionada e análise de mercado em tempo real como proxy de relevância.

**Referências principais:**
- Reimers & Gurevych (2019) — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
- Nogueira & Cho (2019) — Passage Re-ranking with BERT
- Salton & Buckley (1988) — Term-weighting approaches in automatic text retrieval
