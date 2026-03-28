# SIRS — Sistema Inteligente de Recrutamento e Seleção

Sistema baseado em NLP e similaridade semântica para automatizar a triagem e avaliação de currículos, combinando aderência aos requisitos da vaga com tendências de mercado.

---

## Sumário

- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e configuração](#instalação-e-configuração)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Rodando o projeto](#rodando-o-projeto)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Como o sistema avalia currículos](#como-o-sistema-avalia-currículos)
- [Workflow do processo seletivo](#workflow-do-processo-seletivo)
- [Endpoints da API](#endpoints-da-api)
- [Testes](#testes)
- [Comandos úteis](#comandos-úteis)

---

## Visão geral

O SIRS automatiza a triagem inicial de candidatos em duas etapas:

**1ª avaliação — Aderência à vaga (peso 60%)**
O RH preenche apenas o nome da vaga e os requisitos em texto livre. O sistema usa o modelo `all-MiniLM-L6-v2` para vetorizar os requisitos e o currículo, calculando a similaridade de cosseno entre os dois.

**2ª avaliação — Aderência ao mercado (peso 40%)**
O Market Analyzer coleta dados de vagas reais (Adzuna API ou Kaggle) e identifica as skills mais demandadas para aquele cargo. O currículo é avaliado contra esse ranking de mercado.

**Score final**
```
score_curriculo = (score_rh × 0.60) + (score_mercado × 0.40)
```

Após a triagem automática, o RH conduz entrevistas (triagem e técnica) e o score consolidado final combina os três componentes:

```
score_total = (score_curriculo × 0.50) + (score_rh × 0.25) + (score_tecnico × 0.25)
```

---

## Arquitetura

```
clientes (React SPA / sistema externo / candidato)
                    ↓
         FastAPI — API Gateway
         (REST · JWT Auth · Webhook receiver)
                    ↓
    ┌───────────────┼───────────────┐
    │               │               │
Candidatos      Entrevistas      Vagas
  Service         Service        Service
    │               │               │
    └───────────────┼───────────────┘
                    ↓
         Motor de Inteligência
    ┌───────────────┬───────────────┐
    │               │               │
Resume Parser  Matching Engine  Market Analyzer
PyMuPDF+spaCy  sentence-trans.  Adzuna/Kaggle
                    ↓
         Celery Worker (Redis broker)
                    ↓
    ┌───────────────┬───────────┐
    │               │           │
PostgreSQL       JSONB        Redis
(dados rel.)  (embeddings)   (filas)
```

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| NLP / IA | sentence-transformers (`all-MiniLM-L6-v2`), spaCy, scikit-learn |
| Extração de PDF | PyMuPDF |
| Filas / Background | Celery, Redis |
| Banco de dados | PostgreSQL 16 |
| Autenticação | JWT (python-jose) |
| Frontend | React (Sprint 3) |
| Infraestrutura | Docker, Docker Compose |
| CI | GitHub Actions (Ruff + pytest) |

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado
- [WSL2](https://learn.microsoft.com/pt-br/windows/wsl/install) com Ubuntu 22.04 (Windows)
- Git configurado
- Conta no GitHub

> **Windows:** todo o desenvolvimento deve ser feito dentro do filesystem do Ubuntu (`~/projetos/sirs`), não em `/mnt/c/`. O Docker tem desempenho muito inferior acessando o filesystem do Windows.

---

## Instalação e configuração

### 1. Clonar o repositório

```bash
cd ~/projetos
git clone https://github.com/JuliaDuran15/SIRS-Sistema-Inteligente-de-Recrutamento-e-Selecao.git sirs
cd sirs
```

### 2. Criar o arquivo de variáveis de ambiente

```bash
cp backend/.env.example backend/.env
```

Edite `backend/.env` com suas configurações (veja a seção [Variáveis de ambiente](#variáveis-de-ambiente)).

### 3. Build e subida dos containers

```bash
docker compose up --build
```

> A primeira execução baixa o modelo `all-MiniLM-L6-v2` (~400MB) e o modelo do spaCy. Pode levar 5–10 minutos dependendo da conexão. As execuções seguintes são rápidas.

### 4. Rodar as migrações do banco

```bash
docker compose exec api alembic upgrade head
```

### 5. Verificar que tudo está rodando

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

Acesse a documentação interativa da API em: `http://localhost:8000/docs`

---

## Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha:

```env
# Banco de dados
DATABASE_URL=postgresql://sirs:sirs123@db:5432/sirs_db

# Celery (Redis como broker)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Segurança — gere com: openssl rand -hex 32
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria

# Ambiente
ENVIRONMENT=development

# APIs externas (opcionais)
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

> O arquivo `.env` está no `.gitignore` e nunca deve ser commitado.

---

## Rodando o projeto

### Subir todos os serviços

```bash
docker compose up
```

### Subir em background

```bash
docker compose up -d
```

### Ver os serviços rodando

```bash
docker compose ps
```

Devem aparecer 4 serviços com status `running` ou `healthy`:

| Serviço | Porta | Descrição |
|---|---|---|
| `api` | 8000 | FastAPI — endpoints REST |
| `worker` | — | Celery — processamento em background |
| `db` | 5432 | PostgreSQL — dados relacionais |
| `redis` | 6379 | Redis — broker de filas |

### Parar os serviços

```bash
docker compose down
```

### Parar e apagar os dados do banco

```bash
docker compose down -v
```

---

## Estrutura de pastas

```
sirs/
├── .github/
│   └── workflows/
│       └── lint.yml              # CI: lint + testes a cada push
├── docker/
│   └── Dockerfile.api            # imagem da API e do worker
├── docker-compose.yml
├── docs/                         # documentação adicional
├── frontend/                     # React SPA (Sprint 3)
└── backend/
    ├── .env.example
    ├── pyproject.toml            # config do Ruff (linter)
    ├── requirements.txt
    ├── migrations/               # migrações Alembic
    └── app/
        ├── main.py               # inicialização do FastAPI
        ├── ai/
        │   ├── tasks.py          # tarefas Celery (background)
        │   ├── resume_parser.py  # extração de texto e skills (Sprint 2)
        │   ├── matching_engine.py# cálculo de scores (Sprint 2)
        │   └── market_analyzer.py# análise de tendências de mercado (Sprint 2)
        ├── api/
        │   └── endpoints/
        │       ├── candidatos.py
        │       ├── vagas.py
        │       └── entrevistas.py
        ├── core/
        │   ├── config.py         # variáveis de ambiente (pydantic-settings)
        │   └── celery_app.py     # configuração do Celery
        ├── db/
        │   ├── session.py        # engine e SessionLocal
        │   └── base.py           # importa todos os models para o Alembic
        ├── models/               # SQLAlchemy ORM
        │   ├── candidato.py
        │   ├── vaga.py
        │   ├── candidatura.py
        │   └── entrevista.py
        ├── schemas/              # Pydantic (request / response)
        └── services/             # lógica de negócio
```

---

## Como o sistema avalia currículos

### Pipeline de processamento (executado em background via Celery)

```
PDF do currículo
      ↓
PyMuPDF — extrai texto bruto
      ↓
spaCy NER — identifica entidades (skills, tecnologias, tempo de exp.)
      ↓
all-MiniLM-L6-v2 — vetoriza o texto completo (384 dimensões)
      ↓
┌─────────────────────┬──────────────────────────┐
│  1ª avaliação       │  2ª avaliação             │
│  Cosine similarity  │  Skills × ranking mercado │
│  vetor vaga ×       │  (Adzuna / Kaggle)        │
│  vetor currículo    │                           │
│  peso: 60%          │  peso: 40%                │
└─────────────────────┴──────────────────────────┘
                      ↓
              Score curricular (0–100)
              + Breakdown por skill
              + Explicação XAI (gaps identificados)
```

### Por que embeddings e não TF-IDF

O modelo `all-MiniLM-L6-v2` captura semântica — "Python developer" e "desenvolvedor backend" geram vetores próximos mesmo sendo textos diferentes. TF-IDF não consegue isso, pois compara apenas palavras exatas.

| Par | TF-IDF | Embedding |
|---|---|---|
| "AWS" × "Amazon Web Services" | 0.00 | ~0.94 |
| "Python dev" × "desenvolvedor backend" | 0.00 | ~0.82 |
| "banco de dados" × "PostgreSQL" | 0.00 | ~0.71 |

---

## Workflow do processo seletivo

```
Entrada do candidato
(webhook externo ou cadastro manual pelo RH)
          ↓
    [novo] → [aguardando_processamento] → [processando_curriculo]
          ↓
    [triagem_pendente]
          ↓
    RH revisa score e ranking
          ↓
    ┌─────────────────┐
    │                 │
[reprovado_triagem] [aprovado_triagem]
    ↓                 ↓
[banco_talentos]  [entrevista_rh_agendada]
                      ↓
                  [entrevista_rh_realizada]
                      ↓
              ┌───────────────────┐
              │                   │
          [reprovado_rh]  [entrevista_tec_agendada]
              ↓                   ↓
          [banco_talentos]  [entrevista_tec_realizada]
                                  ↓
                          ┌───────────────────┐
                          │                   │
                   [reprovado_tecnico]  [decisao_pendente]
                          ↓                   ↓
                   [banco_talentos]    RH decide
                                       ↓
                              ┌────────────────┐
                              │                │
                         [contratado]   [nao_aprovado]
```

---

## Endpoints da API

A documentação completa e interativa está disponível em `http://localhost:8000/docs` (Swagger UI).

### Saúde

```
GET  /health
```

### Candidatos

```
POST /candidatos              — cadastro manual pelo RH
POST /webhook/candidatos      — recebe candidatos de sistemas externos
GET  /candidatos/{id}         — perfil completo com score e skills
```

### Vagas

```
POST /vagas                   — criar vaga (nome + requisitos em texto livre)
GET  /vagas/{id}/ranking      — ranking de candidatos com scores e XAI
```

### Entrevistas

```
POST /entrevistas             — agendar entrevista (RH ou técnica)
PUT  /entrevistas/{id}        — registrar resultado (score + anotações)
GET  /candidaturas/{id}/entrevistas — listar entrevistas de uma candidatura
```

### Tarefas (Celery)

```
GET  /tarefas/{task_id}       — consultar status do processamento do currículo
```

---

## Testes

### Rodar todos os testes

```bash
docker compose exec api pytest tests/ -v
```

### Rodar com cobertura

```bash
docker compose exec api pytest tests/ -v --cov=app --cov-report=term-missing
```

### Rodar o linter

```bash
docker compose exec api ruff check app/
```

---

## Comandos úteis

```bash
# Logs em tempo real de um serviço específico
docker compose logs api -f
docker compose logs worker -f

# Entrar no container da API
docker compose exec api bash

# Entrar no banco de dados
docker compose exec db psql -U sirs -d sirs_db

# Ver filas do Redis
docker compose exec redis redis-cli -n 0 llen celery

# Criar nova migração após alterar um model
docker compose exec api alembic revision --autogenerate -m "descricao"
docker compose exec api alembic upgrade head

# Voltar uma migração
docker compose exec api alembic downgrade -1

# Ver workers Celery ativos
docker compose exec worker celery -A app.core.celery_app inspect active

# Rebuild de um serviço específico
docker compose up --build api
```

---

## CI — GitHub Actions

A cada push nas branches `main` e `develop`, o pipeline executa automaticamente:

1. Lint com Ruff (`ruff check app/`)
2. Testes com pytest (`pytest tests/ -v`)

O status aparece na aba **Actions** do repositório no GitHub.

---

## Contexto acadêmico

Este sistema foi desenvolvido como Trabalho de Conclusão de Curso, propondo uma abordagem baseada em NLP e similaridade semântica para o problema de triagem de currículos — contornando a ausência de datasets rotulados (contratado/não contratado) através de aprendizado não supervisionado e métricas de similaridade vetorial.

**Referências técnicas principais:**
- Reimers & Gurevych (2019) — Sentence-BERT
- Salton & Buckley (1988) — TF-IDF e similaridade de cosseno
- Mikolov et al. (2013) — Word2Vec e representações distribuídas