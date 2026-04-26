# SIRS — Sistema Inteligente de Recrutamento e Seleção

Sistema web completo para automação do processo seletivo, combinando NLP semântico, análise de mercado em tempo real e gestão de entrevistas com controle de acesso por papel.

---

## Sumário

- [Visão geral](#visão-geral)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Papéis e permissões](#papéis-e-permissões)
- [Pipeline do processo seletivo](#pipeline-do-processo-seletivo)
- [Como o sistema avalia currículos](#como-o-sistema-avalia-currículos)
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

O SIRS automatiza a triagem de candidatos em três camadas:

**1 — Score curricular (automático, via Celery)**

O RH faz upload do currículo em PDF. O sistema extrai o texto, gera um embedding de 384 dimensões e calcula dois scores:

| Score | O que mede | Peso padrão |
|---|---|---|
| Aderência à vaga | Similaridade de cosseno entre currículo e requisitos da vaga | 60% |
| Aderência ao mercado | Similaridade entre currículo e o vetor das top skills do mercado | 40% |

```
score_curriculo = (score_rh × 0.60) + (score_mercado × 0.40)
```

**2 — Entrevistas (RH e técnica)**

RH agenda e registra a entrevista de RH. O gestor técnico registra o resultado da entrevista técnica. Cada entrevista tem score 0–10, anotações livres e listas de pontos fortes/fracos.

**3 — Score consolidado final**

```
score_total = (score_curriculo × 0.50) + (score_rh × 0.25) + (score_técnico × 0.25)
```

Os pesos são configuráveis por vaga pelo RH ou Admin.

**Market Analyzer (automático na criação da vaga)**

Ao criar uma vaga, o sistema dispara em background uma análise de mercado (Kaggle/Adzuna) que identifica as skills mais demandadas para aquele cargo e gera o vetor de mercado usado no score.

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| **Frontend** | React 18, Vite, Tailwind CSS v4 |
| **NLP / IA** | sentence-transformers (`all-MiniLM-L6-v2`), PyMuPDF |
| **Análise de mercado** | Adzuna API, Kaggle LinkedIn Jobs dataset |
| **Banco de dados** | PostgreSQL 16 + pgvector (vetores de 384 dims) |
| **Filas / background** | Celery 5, Redis 7 |
| **Autenticação** | JWT (python-jose, bcrypt) |
| **Infraestrutura** | Docker, Docker Compose |
| **Testes** | pytest, TestClient (FastAPI), banco de testes isolado por transação |

---

## Arquitetura

```
┌─────────────────────────────────────────────┐
│              React SPA (Vite)               │
│  /vagas  /candidatos  /admin  /entrevistas  │
└──────────────────┬──────────────────────────┘
                   │ HTTP /api/*
┌──────────────────▼──────────────────────────┐
│            FastAPI (porta 8000)             │
│  JWT Auth · RBAC · REST · Webhook receiver  │
│                                             │
│  /auth  /vagas  /candidatos  /candidaturas  │
│  /entrevistas  /usuarios                    │
└──────┬─────────────────────┬────────────────┘
       │                     │
       │ SQLAlchemy           │ .delay()
┌──────▼──────┐      ┌───────▼────────────────┐
│ PostgreSQL  │      │    Celery Worker        │
│  + pgvector │      │                         │
│             │      │  processar_curriculo    │
│  candidatos │      │  atualizar_mercado_vaga │
│  vagas      │      └───────┬────────────────┘
│  candidatur.│              │
│  curriculos │    ┌─────────▼──────────────────┐
│  entrevistas│    │      Motor de IA            │
│  usuarios   │    │                             │
└─────────────┘    │  Resume Parser  (PyMuPDF)  │
                   │  Matching Engine (cosine)  │
       ┌───────────│  Market Analyzer (Kaggle/  │
       │           │    Adzuna + TF-IDF)        │
┌──────▼──────┐    └────────────────────────────┘
│    Redis    │
│  (broker +  │
│   results)  │
└─────────────┘
```

---

## Papéis e permissões

O sistema tem 3 papéis com permissões distintas:

| Ação | RH | Gestor técnico | Admin |
|---|:---:|:---:|:---:|
| Cadastrar candidato | ✓ | — | ✓ |
| Criar / editar vaga | ✓ | — | ✓ |
| Editar pesos da vaga | ✓ | — | ✓ |
| Visualizar ranking de candidatos | ✓ | ✓ | ✓ |
| Aprovar / reprovar triagem | ✓ | — | ✓ |
| Fazer upload de currículo | ✓ | — | ✓ |
| Agendar entrevista (RH ou técnica) | ✓ | — | ✓ |
| Registrar resultado entrevista RH | ✓ | — | ✓ |
| Registrar resultado entrevista técnica | — | ✓ | ✓ |
| Tomar decisão final (contratar etc.) | ✓ | — | ✓ |
| Gerenciar usuários (criar / desativar) | — | — | ✓ |
| Receber webhook externo | sistema | sistema | sistema |

> O webhook (`POST /candidatos/webhook`) não exige autenticação — é chamado por sistemas externos (ATS, HRIS).

---

## Pipeline do processo seletivo

```
Candidato entra
(cadastro RH ou webhook externo)
          │
          ▼
      [NOVO]
          │  RH faz upload do PDF
          ▼
[AGUARDANDO_PROCESSAMENTO]
          │  Celery pega a task
          ▼
  [PROCESSANDO_CURRICULO]
          │  Embedding gerado, scores calculados
          ▼
   [TRIAGEM_PENDENTE]  ◄── RH analisa ranking
          │
    ┌─────┴──────┐
    ▼            ▼
[REPROVADO   [APROVADO
 TRIAGEM]     TRIAGEM]
    │              │  RH agenda entrevista
    ▼              ▼
[BANCO      [ENTREVISTA_RH_AGENDADA]
TALENTOS]         │  RH registra resultado
                  ▼
         [ENTREVISTA_RH_REALIZADA]
                  │
         ┌────────┴──────────┐
         ▼                   ▼
    [REPROVADO_RH]  [ENTREVISTA_TEC_AGENDADA]
         │                   │  Gestor registra resultado
         ▼                   ▼
    [BANCO          [ENTREVISTA_TEC_REALIZADA]
    TALENTOS]               │
                   ┌────────┴──────────┐
                   ▼                   ▼
           [REPROVADO_TEC]    [DECISAO_PENDENTE]
                   │                   │  RH decide
                   ▼         ┌─────────┼─────────┐
           [BANCO           ▼         ▼         ▼
           TALENTOS]  [CONTRATADO] [NAO_    [BANCO
                                   APROVADO] TALENTOS]
```

Cada transição é registrada no campo `historico` (JSONB) com timestamp, status anterior/posterior e quem fez a ação.

---

## Como o sistema avalia currículos

### Embeddings semânticos vs. TF-IDF

O modelo `all-MiniLM-L6-v2` captura semântica — termos equivalentes ficam próximos no espaço vetorial mesmo com palavras diferentes:

| Par de termos | TF-IDF | Embedding |
|---|:---:|:---:|
| "AWS" × "Amazon Web Services" | 0.00 | ~0.94 |
| "Python dev" × "desenvolvedor backend" | 0.00 | ~0.82 |
| "banco de dados" × "PostgreSQL" | 0.00 | ~0.71 |

### Market Analyzer

Ao criar uma vaga, o sistema detecta a categoria do cargo (tech, direito, RH, engenharia civil, financeiro, marketing, saúde) e coleta dados de:

- **Kaggle** (dataset LinkedIn Jobs, ~120k vagas) — cargos tech
- **Adzuna API** (vagas reais em PT-BR) — outros cargos

Aplica TF-IDF nos textos coletados para extrair as top skills do mercado, gera um vetor médio ponderado e usa esse vetor para avaliar a aderência de cada currículo.

Quando os dados externos são insuficientes (< 10 vagas encontradas), o sistema usa uma lista de skills curadas por categoria como fallback.

### Currículo por candidatura

Cada candidatura tem seu próprio currículo processado — o candidato pode enviar um CV focado em Python para a vaga de Dev e um CV diferente para a vaga de DevOps, sem que um sobrescreva o outro.

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

# Market Analyzer: "kaggle" ou "adzuna" ou "ambos"
MARKET_ANALYZER_SOURCE=kaggle

# Adzuna API (opcional — cadastro gratuito em api.adzuna.com)
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
ADZUNA_COUNTRY=br
```

> Para usar o Kaggle como fonte, coloque o arquivo `postings.csv` do [dataset LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) em `backend/data/postings.csv`.

---

## Populando o banco

### Seed básico (4 vagas, 4 candidatos)

```bash
docker compose exec api python tests/seed.py
```

### Seed completo (dados realistas em todas as etapas)

```bash
docker compose exec api python tests/seed_full.py
```

O seed completo cria:

- **6 usuários** — 2 RH, 3 gestores técnicos, 1 admin
- **10 vagas** — Python, Full Stack, Dados, DevOps, RH, Direito, Civil, Financeiro, UX/UI, Marketing
- **30 candidatos** com formações e perfis variados
- **50 candidaturas** distribuídas em todas as etapas do pipeline, com currículos processados (scores reais via embedding), entrevistas agendadas/realizadas e histórico de transições

Logins após o seed:

| Email | Senha | Papel |
|---|---|---|
| `ana@sirs.com` | `senha123` | RH |
| `bruno@sirs.com` | `senha123` | RH |
| `carlos@sirs.com` | `senha123` | Gestor técnico |
| `daniela@sirs.com` | `senha123` | Gestor técnico |
| `eduardo@sirs.com` | `senha123` | Gestor técnico |
| `admin@sirs.com` | `senha123` | Admin |

---

## Estrutura de pastas

```
sirs/
├── docker-compose.yml
├── docker/
│   ├── Dockerfile.api
│   └── init.sql               # cria extensão pgvector
│
├── backend/
│   ├── .env
│   ├── pyproject.toml         # pytest config
│   ├── migrations/            # Alembic
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── ai/
│       │   ├── tasks.py           # Celery tasks
│       │   ├── resume_parser.py   # PDF → texto → embedding
│       │   ├── matching_engine.py # cálculo de scores
│       │   └── market_analyzer.py # Kaggle/Adzuna + TF-IDF
│       ├── api/
│       │   ├── deps.py
│       │   └── endpoints/
│       │       ├── auth.py
│       │       ├── usuarios.py
│       │       ├── vagas.py
│       │       ├── candidatos.py
│       │       ├── candidaturas.py
│       │       └── entrevistas.py
│       ├── core/
│       │   ├── auth.py            # JWT, hash, guards RBAC
│       │   ├── config.py
│       │   └── celery_app.py
│       ├── db/
│       │   ├── session.py
│       │   ├── base.py            # importa todos os models
│       │   └── ensure_admin.py
│       ├── models/
│       │   ├── usuario.py
│       │   ├── vaga.py
│       │   ├── candidato.py
│       │   ├── candidatura.py     # máquina de estados + histórico
│       │   ├── curriculo.py       # associado à candidatura (não ao candidato)
│       │   └── entrevista.py
│       └── schemas/               # Pydantic request/response
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx               # router + auth guard
│       ├── api.js                 # axios + interceptors
│       ├── components/
│       │   ├── Layout.jsx         # nav com controle por papel
│       │   ├── Badge.jsx
│       │   └── ScoreBar.jsx
│       ├── context/
│       │   └── AuthContext.jsx
│       └── pages/
│           ├── Login.jsx
│           ├── Vagas.jsx
│           ├── VagaDetalhe.jsx    # ranking + edição de pesos
│           ├── Candidatos.jsx
│           ├── EntrevistaDetalhe.jsx  # upload CV, entrevistas, decisão
│           └── AdminUsuarios.jsx  # CRUD de usuários (admin)
│
└── backend/tests/
    ├── conftest.py    # DB de testes, fixtures, factories
    ├── seed.py        # seed básico
    ├── seed_full.py   # seed completo com 50 candidaturas
    ├── test_auth.py
    ├── test_usuarios.py
    ├── test_vagas.py
    ├── test_candidatos.py
    ├── test_candidaturas.py
    ├── test_entrevistas.py
    ├── test_matching_engine.py
    └── test_market_analyzer.py
```

---

## Endpoints da API

Documentação interativa completa: `http://localhost:8000/docs`

### Auth
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/login` | público | Login OAuth2 password flow |
| GET | `/auth/me` | autenticado | Usuário atual |

### Usuários
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/usuarios/` | admin | Criar usuário (RH ou gestor) |
| GET | `/usuarios/` | autenticado | Listar usuários ativos |
| GET | `/usuarios/{id}` | autenticado | Buscar usuário |
| DELETE | `/usuarios/{id}` | admin | Desativar usuário |

### Vagas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/vagas/` | RH, admin | Criar vaga (dispara market analysis) |
| GET | `/vagas/` | autenticado | Listar vagas abertas |
| GET | `/vagas/{id}` | autenticado | Detalhes + ranking de mercado |
| PATCH | `/vagas/{id}/pesos` | RH, admin | Ajustar pesos do score |
| PATCH | `/vagas/{id}/status` | RH, admin | Abrir / pausar / fechar |
| POST | `/vagas/{id}/analisar-mercado` | RH, admin | Re-executar análise de mercado |
| DELETE | `/vagas/{id}` | admin | Fechar vaga |

### Candidatos
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/candidatos/` | RH, admin | Cadastrar candidato |
| POST | `/candidatos/webhook` | público | Receber de sistema externo |
| GET | `/candidatos/` | autenticado | Listar candidatos |
| GET | `/candidatos/{id}` | autenticado | Perfil do candidato |
| PATCH | `/candidatos/{id}` | RH, admin | Atualizar dados |

### Candidaturas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/candidaturas/` | RH, admin | Vincular candidato a vaga |
| GET | `/candidaturas/` | autenticado | Listar (filtrável por `?vaga_id=`) |
| GET | `/candidaturas/{id}` | autenticado | Detalhes + candidato + currículo |
| PATCH | `/candidaturas/{id}/status` | RH, admin | Avançar/reprovar no pipeline |
| POST | `/candidaturas/{id}/curriculo` | RH, admin | Upload PDF (dispara processamento) |

### Entrevistas
| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/entrevistas/` | RH, admin | Agendar entrevista (RH ou técnica) |
| PATCH | `/entrevistas/{id}/resultado` | RH (tipo rh) / gestor (tipo técnica) / admin | Registrar resultado |
| GET | `/entrevistas/candidatura/{id}` | autenticado | Listar entrevistas de uma candidatura |

---

## Frontend — páginas

| Rota | Acesso | Descrição |
|---|---|---|
| `/login` | público | Login |
| `/` | autenticado | Lista de vagas abertas |
| `/vagas/:id` | autenticado | Ranking de candidatos, skills de mercado, edição de pesos |
| `/candidatos` | autenticado | Lista de candidatos |
| `/candidaturas/:id/entrevistas` | autenticado | Perfil do candidato, upload de CV, entrevistas, decisão final |
| `/admin` | admin | Gerenciar usuários (criar RH/gestor, desativar) |

---

## Testes

Os testes usam um banco PostgreSQL dedicado (`sirs_test_db`) com isolamento por transação — cada teste roda em um savepoint que é desfeito ao final, sem afetar o banco principal.

Celery tasks e chamadas ao modelo de embeddings são mockadas para que os testes de API sejam rápidos.

### Rodar todos os testes

```bash
docker compose exec api python -m pytest tests/ -v
```

### Rodar um módulo específico

```bash
# testes de entrevistas
docker compose exec api python -m pytest tests/test_entrevistas.py -v

# só testes de funções puras (sem banco)
docker compose exec api python -m pytest tests/test_matching_engine.py tests/test_market_analyzer.py -v
```

### Cobertura por módulo

| Arquivo | Testes | O que cobre |
|---|:---:|---|
| `test_matching_engine.py` | 23 | Scores RH, mercado, currículo, XAI, score final |
| `test_market_analyzer.py` | 26 | Detecção de categoria, extração de skills, TF-IDF |
| `test_auth.py` | 19 | Login, /me, hash/token, guards RBAC |
| `test_usuarios.py` | 20 | CRUD + guards admin |
| `test_vagas.py` | 27 | CRUD + permissões + market analysis |
| `test_candidatos.py` | 21 | CRUD + webhook + permissões |
| `test_candidaturas.py` | 27 | CRUD + máquina de estados + upload PDF |
| `test_entrevistas.py` | 33 | Agendamento (só RH), registrar resultado, permissões |
| **Total** | **196** | |

---

## Comandos úteis

```bash
# Subir os serviços
docker compose up -d

# Ver status dos containers
docker compose ps

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

# Rodar o seed completo
docker compose exec api python tests/seed_full.py

# Ver workers Celery ativos
docker compose exec worker celery -A app.core.celery_app inspect active

# Ver filas pendentes no Redis
docker compose exec redis redis-cli llen celery
```

---

## Contexto acadêmico

Desenvolvido como Trabalho de Conclusão de Curso, propondo uma abordagem baseada em embeddings semânticos para o problema de triagem de currículos — contornando a ausência de datasets rotulados através de similaridade vetorial não supervisionada e análise de mercado em tempo real.

**Referências principais:**
- Reimers & Gurevych (2019) — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
- Salton & Buckley (1988) — Term-weighting approaches in automatic text retrieval
- Mikolov et al. (2013) — Distributed Representations of Words and Phrases
