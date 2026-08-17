# Organização do Código — SIRS

## Infraestrutura (docker-compose)

| Serviço    | Porta | Papel                              |
|------------|-------|------------------------------------|
| `api`      | 8000  | FastAPI + Uvicorn                  |
| `worker`   | —     | Celery (processa CVs em background)|
| `db`       | 5432  | PostgreSQL 16 + pgvector           |
| `redis`    | 6379  | Broker do Celery                   |
| `frontend` | 3000  | React 18 + Vite                    |

---

## Backend (`backend/app/`)

### `main.py`

Ponto de entrada. Registra todos os routers, roda migrations no boot, inicializa extensões do PostgreSQL.

---

### `core/` — Infraestrutura transversal

| Arquivo               | Responsabilidade                                         |
|-----------------------|----------------------------------------------------------|
| `config.py`           | Variáveis de ambiente (Settings via pydantic)            |
| `auth.py`             | JWT, guards de papel (`RH_OU_ADMIN`, `QUALQUER_PAPEL`)   |
| `email.py`            | SMTP, templates HTML, `enviar_emails_em_lote`            |
| `celery_app.py`       | Instância do Celery                                      |
| `rate_limit.py`       | Rate limit por IP (usado no webhook)                     |
| `logger.py`           | Logger estruturado com prefixo de contexto               |

---

### `models/` — SQLAlchemy ORM

| Arquivo           | Tabela / Conteúdo principal                              |
|-------------------|----------------------------------------------------------|
| `vaga.py`         | Vagas: nome, requisitos, `vetor_vaga`, pesos de score    |
| `candidato.py`    | Candidatos: dados pessoais, formação (JSONB)             |
| `candidatura.py`  | Candidaturas: status, histórico (JSONB), scores          |
| `curriculo.py`    | Currículos: texto extraído, vetores, scores              |
| `entrevista.py`   | Entrevistas: tipo, `score_manual`, anotações             |
| `usuario.py`      | Usuários: papel (`RH` / `GESTOR` / `ADMIN`)              |
| `configuracao.py` | Configurações globais da empresa                         |

---

### `schemas/` — Pydantic (validação e serialização)

Espelha os models: `vaga.py`, `candidato.py`, `candidatura.py`, `entrevista.py`, `usuario.py`, `webhook.py`.

---

### `api/endpoints/` — Routers FastAPI

| Arquivo             | Responsabilidade                                              |
|---------------------|---------------------------------------------------------------|
| `vagas.py`          | CRUD vagas, pesos, requisitos, reranker, recálculo de scores  |
| `candidaturas.py`   | Máquina de estados, triagem em lote, upload de CV             |
| `candidatos.py`     | CRUD candidatos                                               |
| `entrevistas.py`    | Agendar/registrar resultado, envio de email em lote           |
| `auth.py`           | Login JWT, reset de senha                                     |
| `usuarios.py`       | CRUD usuários (admin)                                         |
| `webhook.py`        | Importação em massa JSON/XML                                  |
| `analytics.py`      | Métricas e dashboards                                         |
| `configuracoes.py`  | Configs globais da empresa                                    |

---

### `ai/` — Pipeline de inteligência

| Arquivo                  | O que faz                                                        |
|--------------------------|------------------------------------------------------------------|
| `resume_parser.py`       | PDF → texto, gera vetores (embedding 384d)                       |
| `section_extractor.py`   | Segmenta CV em seções (experiência, skills, formação)            |
| `feature_extractor.py`   | Regex: anos de exp, senioridade, skills, bônus estrutural        |
| `matching_engine.py`     | Calcula `score_rh`, `score_mercado`, `score_total`, XAI          |
| `market_analyzer.py`     | Vetor de mercado por cargo (Kaggle / Adzuna)                     |
| `reranker.py`            | Cross-encoder `BAAI/bge-reranker-base` (lazy load)               |
| `tasks.py`               | Tasks Celery: processar CV, atualizar mercado                    |
| `transcript_analyzer.py` | Analisa transcrição de entrevista via LLM                        |

#### Fórmula de scoring

```text
score_rh (com seções):
  0.60 × sim(vetor_exp_section, vetor_vaga)
+ 0.40 × sim(vetor_cv_completo, vetor_vaga)
+ bonus_estrutural × 0.6

score_curriculo = clamp(score_rh × peso_rh + score_mercado × peso_mercado, 0, 1) × 100

score_total = (score_curriculo/100  × peso_curriculo)
            + (score_entrevista_rh/10  × peso_entrevista_rh)
            + (score_entrevista_tec/10 × peso_entrevista_tec)
```

---

## Frontend (`frontend/src/`)

### `pages/`

| Página                  | Rota                        | Acesso          |
|-------------------------|-----------------------------|-----------------|
| `Login.jsx`             | `/login`                    | público         |
| `EsqueceuSenha.jsx`     | `/esqueceu-senha`           | público         |
| `ResetarSenha.jsx`      | `/resetar-senha`            | público         |
| `Dashboard.jsx`         | `/`                         | todos os papéis |
| `Vagas.jsx`             | `/vagas`                    | todos os papéis |
| `VagaDetalhe.jsx`       | `/vagas/:id`                | todos os papéis |
| `KanbanVaga.jsx`        | `/vagas/:id/kanban`         | todos os papéis |
| `Candidatos.jsx`        | `/candidatos`               | todos os papéis |
| `CandidatoDetalhe.jsx`  | `/candidatos/:id`           | todos os papéis |
| `EntrevistaDetalhe.jsx` | `/entrevistas/:id`          | todos os papéis |
| `Auditoria.jsx`         | `/auditoria`                | só admin        |
| `AdminUsuarios.jsx`     | `/admin/usuarios`           | só admin        |
| `ConfigEmpresa.jsx`     | `/configuracoes`            | só admin        |
| `Perfil.jsx`            | `/perfil`                   | todos os papéis |

### `components/`

| Componente                  | Papel                                                   |
|-----------------------------|---------------------------------------------------------|
| `Layout.jsx`                | Sidebar, navbar; link Auditoria visível só para admin   |
| `ExplicacaoScore.jsx`       | Breakdown de score (aderência, mercado, skills)         |
| `ComparacaoCandidatos.jsx`  | Modal de comparação lado a lado (2–3 candidatos)        |
| `ScoreBar.jsx`              | Barra de progresso de score                             |
| `Badge.jsx`                 | Badge de status de candidatura                          |
| `Icons.jsx`                 | Ícones SVG reutilizáveis                                |
| `ToastContainer.jsx`        | Notificações toast                                      |

### Infraestrutura do frontend

| Arquivo              | Papel                                                  |
|----------------------|--------------------------------------------------------|
| `api.js`             | Axios com interceptor JWT, centraliza todas as chamadas|
| `AuthContext.jsx`    | Estado de autenticação global (React Context)          |
| `App.jsx`            | React Router, rotas protegidas por papel               |
| `useToast.js`        | Hook para disparar toasts                              |

---

## Testes (`backend/tests/`)

| Arquivo                     | Foco                                                        |
|-----------------------------|-------------------------------------------------------------|
| `test_auth.py`              | Login, reset de senha, tokens                               |
| `test_vagas.py`             | CRUD, `rhs_autorizados`, recálculo de scores                |
| `test_candidaturas.py`      | Máquina de estados, triagem em lote, savepoints             |
| `test_entrevistas.py`       | Permissões por papel e por vaga                             |
| `test_feature_extractor.py` | Anos de exp, senioridade, skills, bônus estrutural          |
| `test_matching_engine.py`   | Scores RH/mercado/multi-seção, XAI, score final             |
| `test_market_analyzer.py`   | Detecção de categoria, extração de skills, filtragem EEO    |
| `test_ai_curriculo.py`      | Pipeline completo com CVs reais (`@pytest.mark.slow`)       |
| `test_novos_curriculos.py`  | Relatório de scoring com CVs reais (`@pytest.mark.slow`)    |
| `test_reranker.py`          | Cross-encoder unidade + endpoint, logging, fallback         |

### Scripts utilitários

| Script                     | O que faz                                                   |
|----------------------------|-------------------------------------------------------------|
| `seed_full.py`             | Limpa e repopula o banco com dados de demonstração          |
| `demo_webhook.py`          | Simula envio de candidatos/vagas via webhook (JSON e XML)   |
| `demo_triagem_webhook.py`  | Fluxo completo: webhook → Celery → triagem em lote          |

